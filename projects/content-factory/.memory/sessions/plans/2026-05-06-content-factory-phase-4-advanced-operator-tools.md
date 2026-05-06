# Plan: Content Factory Phase 4 — Advanced Operator Tools

**Spec:** `.memory/sessions/specs/2026-05-06-content-factory-pilot-implementation-rollout.md`
**Status:** planning

---

## Challenge Log

**Problem:** после фаз 1-3 у продукта уже будет usable pilot pipeline, но power-user/operator возможности останутся ограниченными. Нужно добавить advanced tooling так, чтобы не превратить основной cockpit в технический графовый интерфейс.

**Chosen solution:** ввести role-gated operator mode: workflow canvas viewer/editor на базе React Flow, preset versioning/diff, variant comparison и bulk productivity tools, оставляя основной ежедневный путь в виде простого cockpit.

**Alternatives considered:**
1. Оставить только простой cockpit без advanced tooling — отвергнуто, потому что оператору будет сложно тонко настраивать pipeline и анализировать вариации.
2. Сразу открыть full canvas всем пользователям — отвергнуто, потому что это ухудшит UX для маркетинга и ревьюеров.

**Why chosen solution is better:** advanced tooling появляется там, где он нужен, но не ломает продуктовую ставку на управляемый production cockpit.

## Problems

| # | Problem | Solution | Status |
|---|---------|----------|--------|
| 1 | Нет безопасного operator-only canvas | Ввести отдельный role-gated workflow mode на React Flow | pending |
| 2 | Нет version control для preset-ов | Добавить preset history, diff и rollback-ready metadata | pending |
| 3 | Нет удобного сравнения вариантов | Ввести compare runs, side-by-side previews и decision notes | pending |
| 4 | Нет bulk tooling для оператора | Добавить batch actions, template library, preset cloning | pending |
| 5 | Риск перегрузить обычных пользователей | Сохранить простой cockpit по умолчанию и скрыть advanced mode по ролям | pending |

## Phases

### Phase 1: Operator Mode And Workflow Canvas
- **Status:** pending
- **Files:** `apps/web/src/features/workflow-canvas/*`, `apps/web/src/features/operator-mode/*`, `apps/api/app/modules/workflows/*`, `apps/web/tests/workflow-canvas/*`
- **Changes:** добавить отдельный operator mode, workflow canvas viewer/editor на React Flow, node/edge inspector, preset input mapping UI, permission gating по ролям
- **TDD:** UI tests на permission gating, canvas state tests, preset mapping tests, route protection tests
- **Gates:** `make test-web` ✅ | `make typecheck-web` ✅ | operator canvas suite ✅
- **Impact:** расширяет power-user UX и требует аккуратного сохранения совместимости с existing workflow preset model
- **Prompt for launch:**
  ```text
  Read this plan and the rollout spec.
  Implement operator mode and workflow canvas as a role-gated feature.
  Start with permission tests and canvas state tests.
  Do not replace the simple cockpit path.
  ```

### Phase 2: Preset Versioning, Diff, And Variant Comparison
- **Status:** pending
- **Files:** `apps/api/app/modules/workflows/*`, `apps/api/app/modules/variants/*`, `apps/web/src/features/workflow-history/*`, `apps/web/src/features/variants/*`, `apps/api/tests/integration/variants/*`
- **Changes:** реализовать preset history, diff view, variant runs, side-by-side compare, decision notes и simple winner marking для операторов
- **TDD:** tests на immutable version history, diff correctness, variant comparison queries, UI regression tests для compare view
- **Gates:** `make test-api` ✅ | `make test-web` ✅ | variants suite ✅
- **Impact:** делает pipeline более обучаемым и облегчает экспериментирование с графами/параметрами
- **Prompt for launch:**
  ```text
  Read this plan and existing workflow/render models.
  Implement preset history, diff, and variant comparison.
  Start with version-history and comparison tests.
  Keep the data model immutable; create new versions instead of mutating old ones.
  ```

### Phase 3: Operator Productivity Hardening
- **Status:** pending
- **Files:** `apps/web/src/features/bulk-actions/*`, `apps/web/src/features/templates/*`, `apps/api/app/modules/templates/*`, `apps/api/tests/integration/templates/*`
- **Changes:** добавить batch rerun/requeue actions, preset templates, cloning flows, operator notes и faster bulk review tools без изменения core compliance/review rules
- **TDD:** tests на batch permissions, template cloning, bulk action idempotency, UI regressions для operator productivity flows
- **Gates:** `make test-api` ✅ | `make test-web` ✅ | operator productivity suite ✅
- **Impact:** повышает операционную скорость команды и завершает advanced tooling stage
- **Prompt for launch:**
  ```text
  Read this plan, the rollout spec, and existing operator workflows.
  Implement bulk actions and template tooling.
  Start with idempotency and permission tests.
  Do not weaken review/compliance constraints while adding operator shortcuts.
  ```

## Changelog

| Date | Phase | Changes |
|------|-------|---------|
| 2026-05-06 | planning | Сформирован подробный plan для advanced operator tooling |
