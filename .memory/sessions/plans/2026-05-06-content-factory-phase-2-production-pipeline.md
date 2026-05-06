# Plan: Content Factory Phase 2 — Production Pipeline And Render Integration

**Spec:** `.memory/sessions/specs/2026-05-06-content-factory-pilot-implementation-rollout.md`
**Status:** planning

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
| 1 | Нет контракта между продуктом и render backend | Ввести `WorkflowPreset` с версионируемым workflow JSON и input/output mapping | pending |
| 2 | Нет async execution lifecycle | Ввести `RenderJob`, `JobAttempt`, idempotent worker tasks и retry budget | pending |
| 3 | Нет provider abstraction | Реализовать adapters для ComfyUI, voice generation и packaging | pending |
| 4 | Нет operator visibility по задачам | Добавить live job status через SSE и job detail UI | pending |
| 5 | Нет publish package | Собирать финальный bundle: video, cover, title, caption, hashtags, audit metadata | pending |

## Phases

### Phase 1: Workflow Presets And Provider Contracts
- **Status:** pending
- **Files:** `apps/api/app/modules/workflows/*`, `apps/api/app/modules/providers/*`, `apps/api/app/modules/render/*`, `packages/contracts/*`, `apps/worker/app/providers/*`
- **Changes:** ввести сущности `WorkflowPreset`, `RenderJob`, `JobAttempt`; определить provider interfaces `WorkflowEngineProvider`, `VoiceProvider`, `PackagingProvider`; хранить workflow JSON как immutable versioned artifact с input/output mapping
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
- **Status:** pending
- **Files:** `apps/worker/app/jobs/*`, `apps/worker/app/orchestration/*`, `apps/api/app/modules/render/*`, `apps/api/app/modules/events/*`, `apps/api/tests/integration/render/*`, `apps/web/src/features/jobs/*`
- **Changes:** реализовать job enqueueing, attempt lifecycle, retry budget, timeout/failure handling, idempotent callbacks, SSE-стрим статусов, queue/job detail screens и operator actions `retry`, `cancel`, `requeue`
- **TDD:** worker integration tests с mock ComfyUI adapter, timeout/retry tests, SSE contract tests, UI tests для job detail/status updates
- **Gates:** `make test-api` ✅ | `make test-worker` ✅ | `make test-web` ✅ | render integration suite ✅
- **Impact:** впервые добавляет настоящую асинхронную генерацию и повышает требования к queue/state consistency
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
