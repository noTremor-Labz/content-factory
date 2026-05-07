# Plan: Content Factory Phase 2 — Production Pipeline And Render Integration

**Spec:** `.memory/sessions/specs/2026-05-06-content-factory-pilot-implementation-rollout.md`
**Status:** in_progress

---

## Challenge Log

**Problem:** после фазы 1 у системы будет control plane, но не будет реального media execution path. Нужно интегрировать render/backend слой так, чтобы ComfyUI остался заменяемым workflow engine, а не стал внутренней частью control plane.

**Chosen solution:** ввести immutable workflow presets, provider adapters, render job orchestration через worker-слой, live status updates и export package, не открывая свободное редактирование графа для всех пользователей.

**Alternatives considered:**
1. Давать пользователю raw ComfyUI граф прямо в MVP — отвергнуто, потому что это перегрузит неоператорских пользователей и замедлит пилот.
2. Строить собственный graph executor вместо ComfyUI — отвергнуто, потому что это не соответствует бизнес-ограничениям и сильно удлиняет путь до пилота.

**Why chosen solution is better:** такой подход связывает control plane и render plane минимальным, но устойчивым контрактом и оставляет место для будущего operator-only canvas.

## Problems

| # | Problem | Solution | Status |
|---|---------|----------|--------|
| 1 | Нет контракта между продуктом и render backend | Ввести `WorkflowPreset` с версионируемым workflow JSON и input/output mapping | completed |
| 2 | Нет async execution lifecycle | Ввести `RenderJob`, `JobAttempt`, idempotent worker tasks и retry budget | completed |
| 3 | Нет provider abstraction | Реализовать adapters для ComfyUI, voice generation и packaging | in_progress / ComfyUI workflow executor complete |
| 4 | Нет operator visibility по задачам | Добавить live job status через SSE и job detail UI | completed |
| 5 | Нет publish package | Собирать финальный bundle: video, cover, title, caption, hashtags, audit metadata | pending |

## Phases

### Phase 1: Workflow Presets And Provider Contracts
- **Status:** completed
- **Files:** `apps/api/src/content_factory_api/modules/workflows.py`, `apps/api/src/content_factory_api/modules/render.py`, `apps/api/src/content_factory_api/modules/models.py`, `apps/api/src/content_factory_api/modules/schemas.py`, `apps/api/src/content_factory_pipeline/providers.py`, `apps/worker/src/content_factory_worker/providers.py`, `apps/api/alembic/versions/20260506_0002_render_contracts.py`, `packages/contracts/*`
- **Changes:** введены сущности `WorkflowPreset`, `RenderJob`, `JobAttempt`; добавлен shared provider registry для `comfyui` / `none` / `ffmpeg`; workflow preset хранится как immutable versioned artifact с input/output mapping; render job снапшотит resolved inputs и сразу создает первый queued attempt
- **TDD:** tests на preset validation, version immutability, mapping serialization, provider contract adapters
- **Gates:** `make lint-api` ✅ | `make typecheck-api` ✅ | `make test-api` ✅
- **Impact:** задает стабильную прослойку между бизнес-логикой и render backend
- **Prompt for launch:**
  ```text
  Read this plan and the rollout spec.
  Implement the workflow preset and provider contract layer first.
  Start with validation and serialization tests.
  Do not add free-form canvas editing.
  ```

### Phase 2: Worker Orchestration, Retries, And Live Status
- **Status:** in_progress / provider and live-status slices complete
- **Files:** `apps/worker/src/content_factory_worker/orchestration.py`, `apps/worker/src/content_factory_worker/jobs/render.py`, `apps/worker/src/content_factory_worker/queue.py`, `apps/worker/src/content_factory_worker/executors/comfyui.py`, `apps/api/src/content_factory_api/modules/render.py`, `apps/api/src/content_factory_api/modules/models.py`, `apps/api/src/content_factory_api/modules/schemas.py`, `apps/api/alembic/versions/20260506_0003_render_attempt_response_payload.py`, `apps/worker/tests/test_render_orchestration.py`, `apps/worker/tests/test_comfyui_executor.py`, `apps/web/src/features/render/RenderPanel.tsx`, `packages/contracts/*`
- **Changes:** реализованы Dramatiq enqueue при создании render job, typed worker executor contract, attempt lifecycle `queued -> running -> succeeded/failed`, retry budget enforcement с созданием следующей queued attempt, response payload persistence, idempotent skip terminal jobs, settings-driven ComfyUI HTTP executor, authenticated SSE stream `GET /api/render-jobs/{id}/events`, and cockpit Render queue/detail UI. Operator actions остаются следующим slice.
- **TDD:** worker orchestration tests для success, retry queueing, exhausted failure и terminal idempotency; ComfyUI executor tests для submit/history/status/timeout/factory; render API regression + SSE stream test; cockpit render route test; generated OpenAPI/TS contract update.
- **Gates:** `make lint-api` ✅ | `make typecheck-api` ✅ | `make test-api` ✅ | `make generate-contracts` ✅ | `make lint-web` ✅ | `make typecheck-web` ✅ | `make test-web` ✅
- **Impact:** добавляет первый настоящий server-side async execution lifecycle и operator visibility; queue/state consistency, provider submission/polling, and render UI path покрыты тестами. Packaging/export still pending.
- **Prompt for launch:**
  ```text
  Read this plan and the implemented provider contracts.
  Implement async job orchestration and live status handling.
  Start with worker integration tests and timeout/retry scenarios.
  Keep tasks idempotent and retries budgeted.
  ```

### Phase 3: Packaging, Export, And Operator Flow
- **Status:** pending
- **Files:** `apps/api/app/modules/export/*`, `apps/worker/app/jobs/packaging/*`, `apps/web/src/features/export/*`, `apps/web/src/features/content/*`, `apps/api/tests/integration/export/*`
- **Changes:** собрать export pipeline через FFmpeg packaging, prepare publish package, attach audit metadata, allow operator to download/export final bundle after approve
- **TDD:** packaging tests, export manifest tests, end-to-end flow `approved content -> render complete -> export bundle`
- **Gates:** `make test-api` ✅ | `make test-worker` ✅ | `make test-web` ✅ | export regression suite ✅
- **Impact:** закрывает production pipeline loop до ручной публикации
- **Prompt for launch:**
  ```text
  Read this plan, the rollout spec, and existing render job flow.
  Implement packaging and publish package export.
  Start with export manifest tests and packaging regression checks.
  Do not implement direct autoposting.
  ```

## Changelog

| Date | Phase | Changes |
|------|-------|---------|
| 2026-05-06 | planning | Сформирован подробный plan для production pipeline и render integration |
| 2026-05-06 | workflow-presets-provider-contracts | Реализованы immutable workflow presets, render job/job attempt contracts, shared provider registry и обновленные OpenAPI/TS contracts |
| 2026-05-07 | worker-orchestration | Добавлены Dramatiq enqueue, worker attempt lifecycle, retry budget enforcement, response payload persistence и orchestration tests |
| 2026-05-07 | provider-live-status | Добавлены ComfyUI HTTP executor, authenticated render job SSE stream, cockpit Render route, and regenerated contracts |
