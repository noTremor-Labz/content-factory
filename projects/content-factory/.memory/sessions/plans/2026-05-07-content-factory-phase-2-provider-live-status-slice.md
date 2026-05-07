# Plan: Content Factory Phase 2 — Provider Adapter And Live Status Slice

**Spec:** `.memory/sessions/specs/2026-05-06-content-factory-pilot-implementation-rollout.md`
**Research:** `.memory/sessions/research/2026-05-07-comfyui-provider-live-status.md`
**Parent plan:** `.memory/sessions/plans/2026-05-06-content-factory-phase-2-production-pipeline.md`
**Status:** completed

---

## Challenge Log

**Problem:** render jobs now have server-side orchestration, but no configured provider
can execute media work and operators cannot see live render state in the cockpit.

**Chosen solution:** add a settings-driven ComfyUI HTTP executor, an authenticated SSE
stream for render job snapshots, generated contract updates, and a compact Render cockpit
route with queue/detail controls.

**Alternatives considered:**
1. Mark jobs succeeded immediately after ComfyUI submission — rejected because it confuses
   queue acceptance with render completion.
2. Build a WebSocket bridge from ComfyUI to the API — rejected for this slice because it
   adds an event subsystem before the pilot needs it.
3. Keep polling only from the frontend — rejected because it misses worker/provider
   progress and gives operators less reliable state during long renders.

**Why chosen solution is better:** it directly closes the next Phase 2 gap while preserving
the existing `RenderExecutor` boundary and keeping ComfyUI replaceable.

## Challenge Loop

1. **Does this solve the problem?** Yes. The executor gives render jobs a real provider path,
   the SSE stream exposes live backend state, and the cockpit route lets operators inspect it.
2. **Is this the most efficient solution?** Yes for the pilot. Polling inside the worker uses
   the current retry/attempt lifecycle and avoids a premature event broker or callback service.
3. **Is there code for code's sake?** No. Changes are limited to provider execution, render
   status API/contracts, and the minimum cockpit UI needed to use them.

## Problems

| # | Problem | Solution | Status |
|---|---------|----------|--------|
| 1 | Worker has only `UnconfiguredRenderExecutor` | Add `ComfyUiRenderExecutor` and settings-driven factory | completed |
| 2 | Provider success/failure is not persisted | Store provider job id and response payload through existing attempt fields | completed |
| 3 | API has no live status endpoint | Add authenticated `GET /api/render-jobs/{id}/events` SSE stream | completed |
| 4 | Cockpit cannot list presets/jobs | Add client types/calls and Render route | completed |
| 5 | Contracts can drift | Regenerate OpenAPI and TypeScript contracts | completed |

## Phases

### Phase 1: Provider Executor
- **Status:** completed
- **Files:** `apps/worker/src/content_factory_worker/config.py`,
  `apps/worker/src/content_factory_worker/jobs/render.py`,
  `apps/worker/src/content_factory_worker/executors/comfyui.py`,
  `apps/worker/tests/test_comfyui_executor.py`,
  `apps/worker/tests/test_worker_config.py`
- **Changes:** implement request build, optional API key header, local/cloud status polling,
  terminal success/failure mapping, timeout failure, and executor factory fallback.
- **TDD:** tests for submit payload, completed local history, failed cloud status, timeout,
  and unconfigured fallback.
- **Gates:** `make lint-api` ✅ | `make typecheck-api` ✅ | `make test-api` ✅
- **Impact:** worker jobs can now complete against a configured provider; local dev remains
  explicit opt-in via env.

### Phase 2: Live Status API
- **Status:** completed
- **Files:** `apps/api/src/content_factory_api/modules/render.py`,
  `apps/api/src/content_factory_api/modules/schemas.py`,
  `apps/api/tests/test_render_contracts.py`,
  `packages/contracts/*`
- **Changes:** add SSE endpoint that emits initial/current snapshots and closes on terminal
  status or client disconnect; add schema and contract coverage.
- **TDD:** tests for event auth, initial event payload, and terminal snapshot.
- **Gates:** `make generate-contracts` ✅ | `make test-api` ✅
- **Impact:** no schema migration; endpoint reads existing render data only.

### Phase 3: Cockpit Render View
- **Status:** completed
- **Files:** `apps/web/src/shared/api/client.ts`, `apps/web/src/shared/api/types.ts`,
  `apps/web/src/features/render/RenderPanel.tsx`, `apps/web/src/app/routes.ts`,
  `apps/web/src/app/App.tsx`, `apps/web/src/app/App.test.tsx`
- **Changes:** load workflow presets/render jobs, create render jobs for planned/approved
  content, subscribe to selected job SSE, and show attempts/provider payloads.
- **TDD:** UI test for render route listing jobs and creating a render job.
- **Gates:** `make lint-web` ✅ | `make typecheck-web` ✅ | `make test-web` ✅
- **Impact:** cockpit gains operator visibility without changing the existing review flow.

## Changelog

| Date | Phase | Changes |
|------|-------|---------|
| 2026-05-07 | planning | Added slice research, Challenge Loop, and phased implementation plan |
| 2026-05-07 | provider-executor | Added settings-driven ComfyUI HTTP executor, worker factory, and provider tests |
| 2026-05-07 | live-status-api | Added authenticated render job SSE stream and contract regeneration |
| 2026-05-07 | cockpit-render-view | Added Render route, client calls, SSE subscription, queue/detail UI, and UI regression coverage |
