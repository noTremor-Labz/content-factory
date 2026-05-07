# Cross-Agent Handoff: Content Factory — Phase 2 Provider Adapter And Live Status

**Date:** 2026-05-07
**From Agent:** Codex
**To Agent:** any
**Session Duration:** current Codex session

---

## Mission Status

### What was the goal?
Continue Phase 2 from the worker-orchestration handoff using bulletproof, specifically the next slice: real provider adapter plus SSE/job detail UI.

### What got done?
- [x] Added slice research and plan:
  - `.memory/sessions/research/2026-05-07-comfyui-provider-live-status.md`
  - `.memory/sessions/plans/2026-05-07-content-factory-phase-2-provider-live-status-slice.md`
- [x] Added settings-driven ComfyUI execution:
  - `apps/worker/src/content_factory_worker/executors/comfyui.py`
  - `apps/worker/src/content_factory_worker/jobs/render.py`
  - `apps/worker/src/content_factory_worker/config.py`
- [x] Added worker tests for local ComfyUI history success, cloud failed status, timeout, and executor factory fallback:
  - `apps/worker/tests/test_comfyui_executor.py`
  - `apps/worker/tests/test_worker_config.py`
- [x] Added authenticated render job SSE status snapshots:
  - `GET /api/render-jobs/{render_job_id}/events`
  - `apps/api/src/content_factory_api/modules/render.py`
  - `apps/api/src/content_factory_api/modules/schemas.py`
- [x] Added cockpit Render route:
  - `apps/web/src/features/render/RenderPanel.tsx`
  - `apps/web/src/app/App.tsx`
  - `apps/web/src/app/routes.ts`
  - `apps/web/src/shared/api/client.ts`
  - `apps/web/src/shared/api/types.ts`
- [x] Regenerated OpenAPI and TypeScript contracts.
- [x] Updated `.memory/context.md`, parent Phase 2 plan, master rollout plan, and generated snapshot.

### What's blocked?
- [ ] Nothing is blocked for the completed slice.

### What's left?
- [ ] Operator actions: retry, cancel, requeue.
- [ ] FFmpeg packaging/export publish package.
- [ ] Richer preset input-to-node mutation for ComfyUI workflows.
- [ ] Compliance, metrics, and economics remain Phase 3.

---

## Current State

### Branch
`codex/content-factory-phase-1-control-plane-ui`

### Last Commit
`ea8ca2b` — Implement phase 1 control plane and cockpit UI

### Key Files Modified
| File | Change | Why |
|------|--------|-----|
| `apps/worker/src/content_factory_worker/executors/comfyui.py` | Added ComfyUI HTTP executor | Real provider-backed render execution |
| `apps/worker/src/content_factory_worker/jobs/render.py` | Added executor factory | Configure real/unconfigured executor from env |
| `apps/worker/src/content_factory_worker/queue.py` | Rebind actor broker before enqueue | Prevent stale Dramatiq broker in tests/process reuse |
| `apps/api/src/content_factory_api/modules/render.py` | Added SSE stream | Live render status snapshots |
| `apps/web/src/features/render/RenderPanel.tsx` | Added Render queue/detail UI | Operator visibility and render job creation |
| `packages/contracts/*` | Regenerated contracts | Keep typed web client aligned with API |

### Tests Status
- [x] All passing

**Verification run:**
- `make generate-contracts` ✅
- `make lint-api` ✅
- `make typecheck-api` ✅
- `make test-api` ✅
- `make lint-web` ✅
- `make typecheck-web` ✅
- `make test-web` ✅

---

## Architecture Decisions Made

1. **Decision:** ComfyUI executor is synchronous inside worker and polls provider state until terminal or timeout.
   **Why:** It fits the existing `RenderExecutor`/attempt lifecycle without adding a callback/WebSocket bridge yet.
   **Consequences:** Long renders occupy a worker process; acceptable for pilot, revisit when concurrency/load grows.

2. **Decision:** Cockpit live status streams API-owned DB snapshots via SSE rather than connecting directly to ComfyUI.
   **Why:** Operators should see product lifecycle state, not raw provider events.
   **Consequences:** SSE remains simple and stateless; provider-specific progress can be added later through persisted attempt payloads or event tables.

3. **Decision:** Stored `workflow_definition.nodes` is submitted as the ComfyUI prompt.
   **Why:** Current preset contracts do not yet define node-level input mutation targets.
   **Consequences:** Presets must already contain executable workflow nodes; richer mapping is a future enhancement.

---

## Context for Next Agent

### Read First
1. `.memory/context.md`
2. `.memory/sessions/2026-05-07-codex-phase-2-provider-live-status.md`
3. `.memory/snapshots/2026-05-07-phase-2-provider-live-status.md`
4. `.memory/sessions/plans/2026-05-06-content-factory-phase-2-production-pipeline.md`
5. `.memory/sessions/plans/2026-05-07-content-factory-phase-2-provider-live-status-slice.md`

### Known Issues / Warnings
- The git worktree contains earlier Phase 1/Phase 2 uncommitted changes from previous handoffs; do not revert them.
- `COMFYUI_BASE_URL` must be set for real provider execution; blank/absent keeps the worker explicitly unconfigured.
- Cloud vendor selection is still open. The executor supports local/cloud-style routes but the pilot deployment target is not finalized.

### Environment Notes
- Python gate uses `.venv/bin/python`.
- Web gate uses `pnpm --dir apps/web`.
- New env vars in `.env.example`: `COMFYUI_BASE_URL`, `COMFYUI_API_KEY`, `COMFYUI_API_MODE`, `COMFYUI_TIMEOUT_SECONDS`, `COMFYUI_POLL_INTERVAL_SECONDS`, `COMFYUI_REQUEST_TIMEOUT_SECONDS`.

---

## Recommended Next Step

**Action:** Continue Phase 2 with operator render actions (`retry`, `cancel`, `requeue`) or start FFmpeg packaging/export publish-package pipeline.
**Estimated effort:** medium.
**Blocked by:** nothing for local implementation; real ComfyUI deployment target remains an external choice.

---

> **For the receiving agent:** Read this file top to bottom, then read the linked context and snapshot. Do not start coding before understanding the current Phase 2 state.
