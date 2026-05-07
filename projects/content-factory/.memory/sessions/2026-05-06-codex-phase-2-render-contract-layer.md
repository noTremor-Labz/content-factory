# Handoff: Content Factory Phase 2 — Render Contract Layer

**Date:** 2026-05-06
**Agent:** Codex
**Phase:** implementation / phase-2-render-contract-layer

---

## Goal
Запустить `Phase 2` с минимального, но устойчивого backend/contracts слоя между control plane и будущим render orchestration: immutable workflow presets, provider registry, render jobs и job attempts.

## Approach
Вместо преждевременного worker orchestration сначала зафиксирован стабильный контракт. Для этого добавлен shared python-пакет `content_factory_pipeline` с provider registry, новые SQLAlchemy/Alembic сущности `WorkflowPreset`, `RenderJob`, `JobAttempt`, API-роуты для preset/job lifecycle и snapshot-based render-job creation, где входы резолвятся из `content_item`/`brand`/`avatar`/`identity_pack` в момент постановки задачи.

## Done
- [x] Добавлен shared provider registry `comfyui` / `none` / `ffmpeg`
- [x] Добавлены domain enums и Pydantic schemas для workflow bindings, presets, render jobs и attempts
- [x] Добавлены SQLAlchemy модели и Alembic migration `20260506_0002_render_contracts.py`
- [x] Добавлены API endpoints:
  - [x] `POST /api/workflow-presets`
  - [x] `GET /api/workflow-presets`
  - [x] `GET /api/workflow-presets/{id}`
  - [x] `POST /api/render-jobs`
  - [x] `GET /api/render-jobs`
  - [x] `GET /api/render-jobs/{id}`
- [x] Реализована auto-versioning логика для immutable presets
- [x] Реализован input snapshot resolution для render job из domain сущностей
- [x] Render job теперь сразу seed-ит первый queued `JobAttempt`
- [x] Обновлены OpenAPI и generated TypeScript contracts
- [x] Обновлены memory docs для перехода к orchestration slice

## Key Files
- `apps/api/src/content_factory_api/modules/workflows.py`
- `apps/api/src/content_factory_api/modules/render.py`
- `apps/api/src/content_factory_api/modules/models.py`
- `apps/api/src/content_factory_api/modules/schemas.py`
- `apps/api/src/content_factory_pipeline/providers.py`
- `apps/worker/src/content_factory_worker/providers.py`
- `apps/api/alembic/versions/20260506_0002_render_contracts.py`
- `packages/contracts/openapi/content-factory.openapi.json`
- `packages/contracts/src/generated/api.ts`

## Verification
- [x] `make lint-api`
- [x] `make typecheck-api`
- [x] `make test-api`
- [x] `make generate-contracts`

## Result
- Phase 2 теперь начата не с расплывчатой идеи render backend, а с явного stable contract layer.
- API и worker уже делят одну provider vocabulary и один validation shape.
- Следующий slice можно строить поверх существующих `RenderJob`/`JobAttempt`, не меняя базовые contracts.

## Next Step
Перейти к `Phase 2 / Worker Orchestration, Retries, And Live Status`:
- добавить enqueue/worker execution для queued jobs;
- обновлять `RenderJob` и `JobAttempt` lifecycle;
- ввести retry budget enforcement и idempotent worker callbacks;
- затем навесить SSE/job detail UI.

## Snapshot
- **Path:** `.memory/snapshots/2026-05-06-phase-2-render-contract-layer.md`
- **Generated:** 2026-05-06
- **Scope:** workflow presets, provider registry, render jobs/job attempts, OpenAPI/contracts

## Context Note
> Если контекст очистится, сначала прочитай этот handoff, затем snapshot, затем `.memory/context.md`, затем phase-2 plan.
