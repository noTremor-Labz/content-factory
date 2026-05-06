# Plan: Content Factory Phase 3 — Compliance, Metrics, And Economics

**Spec:** `.memory/sessions/specs/2026-05-06-content-factory-pilot-implementation-rollout.md`
**Status:** planning

---

## Challenge Log

**Problem:** работающий pipeline без compliance gate и economics visibility опасен для regulated пилота. Нужно встроить policy checks, risk scoring и metrics loop так, чтобы они не усложнили фазу 1-2, но стали обязательной частью релиза контента.

**Chosen solution:** добавить hard-rule compliance engine, soft-risk scoring с объяснением причин, manual metrics import first, cost/retry accounting и analytics/playbook screens на уже существующем lifecycle.

**Alternatives considered:**
1. Оставить compliance полностью на ручную проверку — отвергнуто, потому что это не создает системного risk memory и audit trail.
2. Делать полноценные API-интеграции с площадками раньше metrics baseline — отвергнуто, потому что это увеличит integration cost без гарантии данных по пилоту.

**Why chosen solution is better:** эта фаза делает продукт пригодным для regulated pilot и одновременно дает первые цифры по эффективности и экономике без лишней интеграционной нагрузки.

## Problems

| # | Problem | Solution | Status |
|---|---------|----------|--------|
| 1 | Нет встроенной policy-модели | Ввести `ComplianceRule`, `ComplianceCheck`, `RiskFlag`, `ReviewDecision` | pending |
| 2 | Нет объяснимого risk score | Комбинировать deterministic rules и soft-risk scoring с reason codes | pending |
| 3 | Нет метрик публикаций | Начать с manual CSV import и mapping на `MetricSnapshot` | pending |
| 4 | Не считаются cost/retry economics | Ввести стоимость попыток, full cost per final asset и approve-rate tracking | pending |
| 5 | Нет аналитического интерфейса | Собрать dashboards для KPI, economics и playbook winners | pending |

## Phases

### Phase 1: Compliance Engine And Approval Gates
- **Status:** pending
- **Files:** `apps/api/app/modules/compliance/*`, `apps/api/app/modules/review/*`, `apps/worker/app/jobs/compliance/*`, `packages/contracts/*`, `apps/web/src/features/compliance/*`
- **Changes:** реализовать hard-rule checks для запрещенных паттернов, soft-risk scoring с reason codes, risk score persistence, блокировку publish/export без финального review decision, compliance summary в UI
- **TDD:** scenario tests на hard fails, soft flags и human override, permission tests на approve/rework flows, UI tests для reviewer screens
- **Gates:** `make test-api` ✅ | `make test-worker` ✅ | `make test-web` ✅ | compliance scenario suite ✅
- **Impact:** делает compliance обязательным gate и влияет на export/review lifecycle
- **Prompt for launch:**
  ```text
  Read this plan and the rollout spec.
  Implement the compliance engine and review gating first.
  Start with hard-fail and override scenario tests.
  Never allow publish/export bypass when compliance decision is missing.
  ```

### Phase 2: Metrics Import And Economics Tracking
- **Status:** pending
- **Files:** `apps/api/app/modules/metrics/*`, `apps/api/app/modules/economics/*`, `apps/worker/app/jobs/metrics/*`, `apps/api/tests/integration/metrics/*`, `apps/web/src/features/metrics/*`
- **Changes:** ввести `MetricSnapshot`, `ImportBatch`, `CostLedger`; реализовать CSV/manual import, mapping на content items, cost aggregation по attempts и финальным роликам, базовый import history
- **TDD:** parser tests, duplicate-row tests, partial import tests, cost aggregation tests, retry-cost reconciliation tests
- **Gates:** `make test-api` ✅ | `make test-worker` ✅ | metrics import suite ✅ | economics aggregation suite ✅
- **Impact:** впервые дает KPI и финансовую обратную связь по контенту и pipeline
- **Prompt for launch:**
  ```text
  Read this plan and the existing content/render models.
  Implement manual metrics import and economics accounting.
  Start with CSV parsing, deduplication, and cost aggregation tests.
  Do not build API-based social connectors yet.
  ```

### Phase 3: Analytics Dashboard And Playbook Loop
- **Status:** pending
- **Files:** `apps/web/src/features/analytics/*`, `apps/web/src/features/playbook/*`, `apps/api/app/modules/analytics/*`, `apps/api/tests/integration/analytics/*`
- **Changes:** собрать KPI dashboards, content performance tables, cost-per-view views, winner detection heuristics и playbook entries, чтобы оператор видел лучшие темы, хуки и форматы
- **TDD:** aggregation query tests, filter/sorting tests, UI regression tests на analytics tables/charts, end-to-end scenario `import metrics -> surface winners`
- **Gates:** `make test-api` ✅ | `make test-web` ✅ | analytics regression suite ✅
- **Impact:** закрывает performance loop от публикации до обновления playbook
- **Prompt for launch:**
  ```text
  Read this plan, the rollout spec, and the metrics/economics layer.
  Implement analytics dashboards and playbook views.
  Start with aggregation tests and finish with UI regression coverage.
  Keep dashboards operator-focused and pilot-specific.
  ```

## Changelog

| Date | Phase | Changes |
|------|-------|---------|
| 2026-05-06 | planning | Сформирован подробный plan для compliance, metrics и economics |
