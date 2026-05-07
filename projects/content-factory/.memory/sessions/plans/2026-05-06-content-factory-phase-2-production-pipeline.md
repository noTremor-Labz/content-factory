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
| 3 | Нет provider abstraction | Реализовать adapters для ComfyUI, voice generation и packaging | in_progress / ComfyUI workflow executor and manifest package builder complete |
| 4 | Нет operator visibility/control по задачам | Добавить live job status через SSE, job detail UI и operator retry/cancel/requeue actions | completed |
| 5 | Нет publish package | Собирать финальный bundle: video, cover, title, caption, hashtags, audit metadata | completed / ZIP manifest export complete; FFmpeg binary normalization pending runtime decision |

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

- **Status:** completed / provider, live-status, and operator action slices complete
- **Files:** `apps/worker/src/content_factory_worker/orchestration.py`, `apps/worker/src/content_factory_worker/jobs/render.py`, `apps/worker/src/content_factory_worker/queue.py`, `apps/worker/src/content_factory_worker/executors/comfyui.py`, `apps/api/src/content_factory_api/modules/render.py`, `apps/api/src/content_factory_api/modules/models.py`, `apps/api/src/content_factory_api/modules/schemas.py`, `apps/api/alembic/versions/20260506_0003_render_attempt_response_payload.py`, `apps/worker/tests/test_render_orchestration.py`, `apps/worker/tests/test_comfyui_executor.py`, `apps/web/src/features/render/RenderPanel.tsx`, `packages/contracts/*`
- **Changes:** реализованы Dramatiq enqueue при создании render job, typed worker executor contract, attempt lifecycle `queued -> running -> succeeded/failed`, retry budget enforcement с созданием следующей queued attempt, response payload persistence, idempotent skip terminal jobs, settings-driven ComfyUI HTTP executor, authenticated SSE stream `GET /api/render-jobs/{id}/events`, cockpit Render queue/detail UI, and role-gated render `cancel`/`retry`/`requeue` actions. Cancelled running renders are not overwritten by worker completion.
- **TDD:** worker orchestration tests для success, retry queueing, exhausted failure, terminal idempotency, and operator cancellation race; ComfyUI executor tests для submit/history/status/timeout/factory; render API regression + SSE stream + operator action tests; cockpit render route/action tests; generated OpenAPI/TS contract update.
- **Gates:** `make lint-api` ✅ | `make typecheck-api` ✅ | `make test-api` ✅ | `make generate-contracts` ✅ | `make lint-web` ✅ | `make typecheck-web` ✅ | `make test-web` ✅
- **Impact:** добавляет первый настоящий server-side async execution lifecycle и operator control; queue/state consistency, provider submission/polling, cancellation race handling, and render UI path покрыты тестами.
- **Prompt for launch:**
  ```text
  Read this plan and the implemented provider contracts.
  Implement async job orchestration and live status handling.
  Start with worker integration tests and timeout/retry scenarios.
  Keep tasks idempotent and retries budgeted.
  ```

### Phase 3: Packaging, Export, And Operator Flow
- **Status:** completed / manifest ZIP publish-package slice complete
- **Files:** `apps/api/src/content_factory_api/modules/exports.py`, `apps/api/src/content_factory_api/modules/models.py`, `apps/api/src/content_factory_api/modules/schemas.py`, `apps/api/alembic/versions/20260507_0004_publish_packages.py`, `apps/worker/src/content_factory_worker/packaging.py`, `apps/worker/src/content_factory_worker/jobs/packaging.py`, `apps/web/src/features/export/ExportPanel.tsx`, `apps/web/src/app/App.tsx`, `apps/web/src/shared/api/client.ts`, `packages/contracts/*`
- **Changes:** добавлен `PublishPackage` lifecycle, API create/list/detail/download, approved+succeeded gates, idempotent package creation per render job, worker ZIP manifest bundle with title/caption/hashtags/provider output, S3-compatible package upload, cockpit Export route, and regenerated OpenAPI/TS contracts.
- **TDD:** API package gate/idempotency/download tests, worker ZIP manifest and missing-output failure tests, cockpit export route test.
- **Gates:** `make generate-contracts` ✅ | `make lint-api` ✅ | `make typecheck-api` ✅ | `make test-api` ✅ | `make lint-web` ✅ | `make typecheck-web` ✅ | `make test-web` ✅ | `PLAYWRIGHT_BASE_URL=http://127.0.0.1:5173 pnpm --dir apps/web test:e2e` ✅
- **Impact:** закрывает production pipeline loop до ручной публикации через download-ready package contract. Actual FFmpeg binary remux/normalization remains a runtime enhancement because `ffmpeg` is not installed in the current local environment.
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
| 2026-05-07 | publish-package-export | Добавлены PublishPackage API/model/migration, worker ZIP manifest packaging, S3 download target, cockpit Export route, tests, and regenerated contracts |
| 2026-05-07 | operator-job-actions | Добавлены role-gated cancel/retry/requeue actions для render jobs и publish packages, worker cancellation guards, cockpit action controls, tests, and regenerated contracts |
