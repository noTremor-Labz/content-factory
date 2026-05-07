# Handoff: Content Factory — FFmpeg Media Normalization

**Date:** 2026-05-07
**Agent:** Codex
**Phase:** Phase 2 final worker media normalization slice

---

## Goal

Complete the publish package worker contract so manual export bundles include a normalized MP4 video file, not only manifest/provider-output references.

## Approach

Kept the slice inside the existing publish package worker. `ZipPublishPackager` now downloads the mapped primary video artifact, normalizes it through an injectable `MediaNormalizer`, writes `video.mp4` into the ZIP, and records normalized artifact metadata in `manifest.json`.

## Done

- [x] Created Bulletproof artifacts:
  - `.memory/sessions/research/2026-05-07-ffmpeg-media-normalization.md`
  - `.memory/sessions/specs/2026-05-07-ffmpeg-media-normalization.md`
  - `.memory/sessions/plans/2026-05-07-ffmpeg-media-normalization.md`
- [x] Added `FfmpegMediaNormalizer`, `MediaNormalizer`, `NormalizedMedia`, and package media-file handling in `apps/worker/src/content_factory_worker/packaging.py`.
- [x] Extended package storage with render artifact download support.
- [x] Added S3-compatible artifact download and same-bucket `s3://...` reference validation in `apps/worker/src/content_factory_worker/jobs/packaging.py`.
- [x] Added `FFMPEG_PATH` and `FFMPEG_TIMEOUT_SECONDS` worker settings in `apps/worker/src/content_factory_worker/config.py` and `.env.example`.
- [x] Updated worker package tests for ZIP `video.mp4`, `normalized_artifacts`, normalizer failure, and missing FFmpeg binary behavior.
- [x] Updated context and rollout plan memory.

## Current Problem / Next Step

Phase 2 is complete at the code-contract level. The next product slice should be `Phase 3 / Compliance, Metrics, And Economics`.

If real media package execution is needed first, install/provision an actual `ffmpeg` binary in the worker runtime. This local machine currently does not have `ffmpeg`; without it, real package processing will fail cleanly with `FFmpeg binary 'ffmpeg' was not found`.

## Key Files

- `apps/worker/src/content_factory_worker/packaging.py` — normalizer, artifact resolution, ZIP bundle construction.
- `apps/worker/src/content_factory_worker/jobs/packaging.py` — S3 artifact download and runtime wiring.
- `apps/worker/tests/test_publish_package_orchestration.py` — behavior coverage and fake normalizer pattern.
- `.memory/sessions/specs/2026-05-07-ffmpeg-media-normalization.md` — acceptance criteria.
- `.memory/sessions/plans/2026-05-07-ffmpeg-media-normalization.md` — completed plan and challenge log.

## Key Decisions Made

- Chose an injectable normalizer instead of requiring FFmpeg during tests, because the local runtime lacks the binary and package behavior still needs deterministic verification.
- Included normalized media inside the existing ZIP rather than adding another API object, because the pilot operator needs one manual download bundle.
- Rejected arbitrary HTTP media fetching for this slice to avoid SSRF/auth questions.

## Code2Prompt Snapshot

- **Path:** `.memory/snapshots/2026-05-07-ffmpeg-media-normalization.md`
- **Generated:** 2026-05-07
- **Scope:** worker packaging code, worker packaging tests, worker config, `.env.example`, and the Bulletproof research/spec/plan artifacts for this slice.

## Gates Status

- [x] Targeted worker package tests: `PYTHONPATH=apps/api/src:apps/worker/src .venv/bin/python -m pytest apps/worker/tests/test_publish_package_orchestration.py -q` (`5 passed`)
- [x] Lint: `make lint-api`
- [x] Type check: `make typecheck-api`
- [x] Tests: `make test-api` (`47 passed`)
- [ ] Security scan: not run; no semgrep installation was added.

## Context Note

> If context is cleared, read this handoff first, then `.memory/snapshots/2026-05-07-ffmpeg-media-normalization.md`, then continue with Phase 3 or worker runtime FFmpeg provisioning.
