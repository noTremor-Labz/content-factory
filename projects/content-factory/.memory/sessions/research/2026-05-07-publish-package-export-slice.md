# Research: Phase 2 Publish Package Export Slice

**Date:** 2026-05-07
**Task size:** M
**Agent:** Codex

## Current Architecture

Phase 2 уже имеет:
- immutable `WorkflowPreset` с `output_mapping`;
- `RenderJob` / `JobAttempt` lifecycle;
- persisted `JobAttempt.response_payload`;
- ComfyUI executor, который сохраняет provider payload;
- cockpit Render route с live status через SSE.

Разрыв сейчас после `RenderJob.succeeded`: оператор видит успешный job, но не получает publish package для ручной публикации.

## Affected Areas

| Area | Why |
|---|---|
| `apps/api/src/content_factory_api/modules/models.py` | Нужна source-of-truth запись publish package |
| `apps/api/src/content_factory_api/modules/schemas.py` | Нужны request/response contracts для UI и OpenAPI |
| `apps/api/src/content_factory_api/modules/exports.py` | Нужны create/list/detail/download endpoints |
| `apps/api/alembic/versions/*` | Нужна миграция таблицы packages |
| `apps/worker/src/content_factory_worker/packaging.py` | Worker должен собирать manifest/package из render output |
| `apps/worker/src/content_factory_worker/jobs/packaging.py` | Dramatiq actor для async package processing |
| `apps/web/src/features/export/*` | Оператору нужен Export cockpit slice |
| `packages/contracts/*` | Typed client должен совпадать с OpenAPI |

## Constraints

- MVP сохраняет manual publish: система готовит bundle, но не постит в соцсети.
- Human review остается gate: package можно готовить только для approved content.
- Package должен опираться на `RenderJob.succeeded` и последний успешный attempt.
- В локальной среде сейчас `ffmpeg` не установлен, поэтому tests не должны зависеть от внешнего binary.
- `ffmpeg` остается packaging provider, но slice должен быть полезным уже сейчас: manifest + ZIP bundle + download target.

## Best Practices Found

- FFmpeg docs describe `ffmpeg` as the command-line converter that reads inputs via `-i` and writes outputs, while MOV/MP4 docs expose `movflags=faststart` for progressive MP4 playback prep: https://ffmpeg.org/ffmpeg.html and https://ffmpeg.org/ffmpeg-formats.html
- Python `zipfile` is a standard-library way to create ZIP archives and supports writing archives in memory/file handles, which is enough for deterministic package assembly in tests: https://docs.python.org/3.12/library/zipfile.html
- Boto3 `upload_fileobj` supports uploading a binary file-like object to S3-compatible storage, matching the existing MinIO/S3 architecture: https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/upload_fileobj.html

## Options Considered

1. **Synchronous API builds package directly**
   - Pros: fewer moving parts.
   - Cons: media packaging can be slow and should not block request/response; worse fit with existing worker architecture.

2. **Worker-driven package job with package model**
   - Pros: aligns with render lifecycle, retry/failure state can be explicit, UI can poll/refresh, future FFmpeg work has a natural home.
   - Cons: more files than a synchronous endpoint.

3. **Delay package until full FFmpeg binary integration**
   - Pros: avoids partial implementation.
   - Cons: leaves production loop broken and makes local tests depend on an external binary that is not present.

## Recommendation

Use option 2: add a `PublishPackage` model and async worker packaging path. The first implementation creates a deterministic ZIP containing `manifest.json`, `title.txt`, `caption.txt`, `hashtags.txt`, and `provider-output.json`, then stores package metadata and an S3 object key. Actual FFmpeg normalization can be added inside the same packager later when the binary/runtime contract is available.
