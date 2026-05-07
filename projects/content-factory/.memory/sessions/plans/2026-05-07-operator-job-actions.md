# Plan: Operator Job Actions

**Spec:** `.memory/sessions/specs/2026-05-07-operator-job-actions.md`
**Status:** completed

---

## Challenge Log

**Problem:** operators need direct recovery controls for render and package jobs without corrupting worker state or audit history.

**Chosen solution:** explicit action endpoints per resource: `/cancel`, `/retry`, `/requeue`, backed by deterministic state transition helpers and cockpit action buttons.

**Alternatives considered:**
1. Single generic `/actions` endpoint — rejected because existing API uses explicit action endpoints and generated contracts are clearer with named routes.
2. Create new render/package rows for every retry — rejected because it hides history and breaks package idempotency per render job.
3. Add package attempts table now — rejected because package work has one current worker step and the table would be speculative for this slice.

**Why chosen solution is better:** it directly satisfies the operator controls, preserves existing data model boundaries, and keeps state transitions auditable and testable.

## Problems

| # | Problem | Solution | Status |
|---|---------|----------|--------|
| 1 | Cancelled running render can be overwritten by worker completion | Refresh job/attempt before worker final commit and skip cancelled state | completed |
| 2 | Failed/cancelled render needs a new attempt | Add manual retry helper that appends queued attempt and enqueues job | completed |
| 3 | Package unique constraint blocks recreating failed packages | Add retry action that resets same package row to queued | completed |
| 4 | Cockpit lacks action affordances | Add status-aware buttons in Render and Export panels | completed |
| 5 | Contracts/tests need alignment | Regenerate contracts and run API/worker/web gates | completed |

## Phases

### Phase 1: API And Worker State Transitions

- **Status:** completed
- **Files:** `domain.py`, `render.py`, `exports.py`, worker orchestration/packaging, API/worker tests
- **Changes:** add statuses/actions, audit logs, enqueue calls, cancellation-aware worker guards
- **TDD:** add API tests for render/package actions and worker tests for cancellation skip behavior
- **Gates:** targeted pytest ✅ | `make lint-api` ✅ | `make typecheck-api` ✅ | `make test-api` ✅
- **Impact:** OpenAPI and generated contracts will change

### Phase 2: Web Cockpit Controls And Contracts

- **Status:** completed
- **Files:** API client/types, `App.tsx`, `RenderPanel.tsx`, `ExportPanel.tsx`, web tests, contracts
- **Changes:** expose valid action buttons and wire refresh messages
- **TDD:** extend cockpit tests for retry/cancel/requeue actions
- **Gates:** `make generate-contracts` ✅ | `make lint-web` ✅ | `make typecheck-web` ✅ | `make test-web` ✅ | Playwright smoke ✅
- **Impact:** UI only; no route/navigation change

## Challenge Loop

1. **Does this solve the problem?** Yes. Every requested operator action maps to a role-gated endpoint and cockpit button; worker safeguards cover the main race.
2. **Is this the most efficient solution?** Yes. Explicit endpoints reuse the existing API style and queue helpers. A generic action endpoint or new attempts table would add more abstraction than the pilot needs.
3. **Is there code for code's sake?** No. Changes are limited to action state transitions, UI wiring, tests, generated contracts, and memory artifacts required by project workflow.

## Changelog

| Date | Phase | Changes |
|------|-------|---------|
| 2026-05-07 | Planning | Created research/spec/plan for operator job actions |
| 2026-05-07 | API/worker | Added render/package cancel, retry, and requeue state transitions with audit logs and worker cancellation guards |
| 2026-05-07 | Web/contracts | Added cockpit action controls and regenerated OpenAPI/TypeScript contracts |
