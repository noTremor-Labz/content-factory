# Plan: Content Factory Pilot Rollout Master Plan

**Spec:** `.memory/sessions/specs/2026-05-06-content-factory-pilot-implementation-rollout.md`
**Status:** planning

---

## Challenge Log

**Problem:** у проекта есть бизнес-видение и high-level архитектурная рекомендация, но нет execution-ready последовательности реализации. Без этапного плана команда будет повторно выбирать стек, границы MVP и порядок работ прямо по ходу разработки.

**Chosen solution:** зафиксировать рекомендуемый pilot stack и разделить реализацию на четыре этапа с отдельными phase-планами: foundation/control plane, production pipeline, compliance/metrics и advanced operator tooling.

**Alternatives considered:**
1. `Next.js full-stack monolith` — отвергнут, потому что хуже масштабируется под media-heavy workers и render/backend split.
2. `Microservices + Temporal/Kafka + Kubernetes` — отвергнут, потому что слишком дорог по ops и complexity для пилота.

**Why chosen solution is better:** она дает быстрый старт, сохраняет ComfyUI как backend, поддерживает regulated human-in-the-loop lifecycle и не создает преждевременный инфраструктурный налог.

## Problems

| # | Problem | Solution | Status |
|---|---------|----------|--------|
| 1 | Стек и repo topology не зафиксированы | Зафиксировать ADR и базовую monorepo-структуру | pending |
| 2 | Нет поэтапного delivery path | Разделить реализацию на 4 последовательных этапа | pending |
| 3 | Review/compliance могут оказаться "поздним модулем" | Встроить review lifecycle с фазы 1, compliance engine с фазы 3 | pending |
| 4 | Async render pipeline не определен | Ввести worker-слой, provider adapters и render job lifecycle | in_progress / execution, live status, publish package export, and operator actions complete |
| 5 | Нет baseline infra и gates | Зафиксировать local/dev topology, CI и quality gates | pending |

## Phases

### Phase 1: Foundation And Control Plane
- **Status:** completed
- **Files:** `.memory/sessions/plans/2026-05-06-content-factory-phase-1-control-plane.md`, будущие `apps/web`, `apps/api`, `apps/worker`, `packages/contracts`, `infra`
- **Changes:** bootstrap monorepo, auth, RBAC, asset intake, avatar/content CRUD, review queue skeleton, audit trail, local infra, CI baseline
- **TDD:** API tests для auth/RBAC/content state, frontend tests для cockpit shell и review queue, smoke E2E для login/upload/review
- **Gates:** `pnpm --filter web lint` ✅ | `pnpm --filter web typecheck` ✅ | `pnpm --filter web test` ✅ | `uv run ruff check` ✅ | `uv run mypy apps/api apps/worker` ✅ | `uv run pytest` ✅
- **Impact:** создает все базовые domain contracts и команды для следующих этапов
- **Prompt for launch:**
  ```text
  Read .memory/sessions/plans/2026-05-06-content-factory-phase-1-control-plane.md.
  Read spec at .memory/sessions/specs/2026-05-06-content-factory-pilot-implementation-rollout.md.
  Implement according to plan. Start with tests.
  Do not modify files outside of the planned monorepo bootstrap, apps/web, apps/api, apps/worker, packages/contracts, infra, and root tooling files.
  After completing:
  1. Self-audit against spec
  2. Verify bugs are real
  3. Impact analysis
  4. Run all phase gates
  ```

### Phase 2: Production Pipeline And Render Integration
- **Status:** in_progress
- **Files:** `.memory/sessions/plans/2026-05-06-content-factory-phase-2-production-pipeline.md`, будущие pipeline/render/export модули в `apps/api`, `apps/worker`, `apps/web`
- **Changes:** workflow presets, provider adapters, render jobs, worker attempt lifecycle/retries, live job status, package export, operator retry/cancel/requeue actions
- **TDD:** ComfyUI executor tests, worker orchestration tests, API SSE/action tests, UI tests для queue/job detail/export/action flow
- **Gates:** phase 1 gates ✅ | worker integration suite ✅ | packaging/export regression suite ✅
- **Impact:** впервые соединяет control plane с render plane, влияет на storage, queueing и domain state machine
- **Prompt for launch:**
  ```text
  Read .memory/sessions/plans/2026-05-06-content-factory-phase-2-production-pipeline.md.
  Read the phase 1 implementation and the rollout spec.
  Implement according to plan. Start with tests.
  Do not modify files outside of pipeline/render/export domains unless required by explicit contracts.
  After completing:
  1. Self-audit against spec
  2. Verify bugs are real
  3. Impact analysis
  4. Run all phase gates
  ```

### Phase 3: Compliance, Metrics, And Economics
- **Status:** pending
- **Files:** `.memory/sessions/plans/2026-05-06-content-factory-phase-3-compliance-metrics.md`, будущие compliance/analytics modules в `apps/api`, `apps/web`, `apps/worker`
- **Changes:** hard-rule compliance engine, soft-risk scoring, manual metrics import, cost/retry accounting, dashboards, playbook loop
- **TDD:** rule-engine tests, import parser tests, cost aggregation tests, frontend analytics screen tests
- **Gates:** previous gates ✅ | compliance scenario suite ✅ | metrics import suite ✅ | analytics regression suite ✅
- **Impact:** добавляет regulatory gates, KPI visibility и economics tracking поверх уже работающего pipeline
- **Prompt for launch:**
  ```text
  Read .memory/sessions/plans/2026-05-06-content-factory-phase-3-compliance-metrics.md.
  Read the rollout spec and phases 1-2 outputs.
  Implement according to plan. Start with tests.
  Do not weaken approval gates or bypass review/compliance transitions.
  After completing:
  1. Self-audit against spec
  2. Verify bugs are real
  3. Impact analysis
  4. Run all phase gates
  ```

### Phase 4: Advanced Operator Tooling
- **Status:** pending
- **Files:** `.memory/sessions/plans/2026-05-06-content-factory-phase-4-advanced-operator-tools.md`, будущие operator/canvas/productivity modules в `apps/web`, `apps/api`
- **Changes:** operator-only workflow canvas, preset versioning/diff, variant comparison, bulk tooling, template library, hardening of operator UX
- **TDD:** UI and domain tests for preset versioning, compare flows, bulk actions, permission boundaries
- **Gates:** previous gates ✅ | advanced operator suite ✅ | role/permission regression suite ✅
- **Impact:** повышает power-user capabilities, не ломая простой cockpit для ежедневных пользователей
- **Prompt for launch:**
  ```text
  Read .memory/sessions/plans/2026-05-06-content-factory-phase-4-advanced-operator-tools.md.
  Read the rollout spec and phases 1-3 outputs.
  Implement according to plan. Start with tests.
  Keep the simple cockpit path intact; advanced tooling must remain role-gated.
  After completing:
  1. Self-audit against spec
  2. Verify bugs are real
  3. Impact analysis
  4. Run all phase gates
  ```

## Changelog

| Date | Phase | Changes |
|------|-------|---------|
| 2026-05-06 | planning | Создан master rollout и отдельные phase-планы для pilot implementation |
| 2026-05-06 | phase-1-bootstrap | Начата реализация Phase 1: поднят monorepo bootstrap, local infra baseline и OpenAPI contract generation |
| 2026-05-06 | phase-1-control-plane-api | Продолжена реализация Phase 1: добавлены auth/RBAC, domain model, Alembic migration, upload/review/audit API и обновленные contracts |
| 2026-05-06 | phase-1-browser-smoke | Phase 1 закрыта Playwright smoke automation и live browser verification |
| 2026-05-06 | phase-2-render-contract-layer | Phase 2 начата: добавлены workflow presets, render jobs/job attempts, provider registry и regenerated API contracts |
| 2026-05-07 | phase-2-worker-orchestration | Добавлены Dramatiq enqueue, worker attempt lifecycle, retry budget enforcement и regenerated contracts |
| 2026-05-07 | phase-2-provider-live-status | Добавлены ComfyUI HTTP executor, render job SSE stream, cockpit Render route и regenerated contracts |
| 2026-05-07 | phase-2-publish-package-export | Добавлены package export API/model, worker ZIP manifest packaging, cockpit Export route и regenerated contracts |
| 2026-05-07 | phase-2-operator-job-actions | Добавлены operator retry/cancel/requeue actions для render jobs и publish packages, worker cancellation guards, cockpit controls и regenerated contracts |
