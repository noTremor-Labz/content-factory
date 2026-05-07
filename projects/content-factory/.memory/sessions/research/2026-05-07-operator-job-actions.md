# Research: Operator Job Actions

**Date:** 2026-05-07
**Task size:** M
**Agent:** Codex

---

## Current Architecture

Render jobs are created by `apps/api/src/content_factory_api/modules/render.py`, persisted as `RenderJob` plus versioned `JobAttempt` rows, and enqueued through `content_factory_worker.queue.enqueue_render_job`. The worker processes one queued attempt at a time in `apps/worker/src/content_factory_worker/orchestration.py`, then transitions the render job to `succeeded`, `failed`, or back to `queued` when automatic retry budget remains.

Publish packages are created by `apps/api/src/content_factory_api/modules/exports.py`, persisted as one `PublishPackage` per render job, and enqueued through `enqueue_publish_package`. The worker assembles packages in `apps/worker/src/content_factory_worker/packaging.py`, then marks packages `ready` or `failed`.

The cockpit UI already has Render and Export panels wired through `apps/web/src/shared/api/client.ts` and refreshed by `apps/web/src/app/App.tsx`.

## Affected Areas

| # | File/Module | Why affected |
|---|-------------|--------------|
| 1 | `apps/api/src/content_factory_api/modules/render.py` | Add role-gated render cancel/retry/requeue actions |
| 2 | `apps/api/src/content_factory_api/modules/exports.py` | Add role-gated package cancel/retry/requeue actions |
| 3 | `apps/api/src/content_factory_api/modules/domain.py` | Add cancelled package status |
| 4 | `apps/worker/src/content_factory_worker/orchestration.py` | Avoid overwriting operator cancellation after provider execution |
| 5 | `apps/worker/src/content_factory_worker/packaging.py` | Skip cancelled packages |
| 6 | `apps/web/src/shared/api/client.ts` | Add action client methods |
| 7 | `apps/web/src/app/App.tsx` | Wire action handlers into panels |
| 8 | `apps/web/src/features/render/RenderPanel.tsx` | Show render action buttons |
| 9 | `apps/web/src/features/export/ExportPanel.tsx` | Show package action buttons |
| 10 | API/worker/web tests and generated contracts | Verify state transitions and keep types aligned |

## Codebase Patterns

- Mutations are exposed as explicit `POST` endpoints such as `/plan`, `/submit-review`, `/approve`, and `/request-rework`.
- Mutating routes use `require_roles(*MUTATION_ROLES)`.
- State changes write audit logs before `commit_or_409`.
- Worker orchestration is deterministic and covered with direct unit tests.
- Web mutations flow through `runCockpitMutation`, then refresh cockpit data.

## Risks and Constraints

- A running worker can finish after an operator cancellation; the worker must refresh state before committing success/failure so it does not overwrite `cancelled`.
- Package rows are unique per render job, so failed/cancelled packages need retry/requeue actions instead of relying on `POST /api/publish-packages` to create another row.
- Requeue should be idempotent and should not create duplicate attempts when a queued attempt already exists.
- Manual retry for render jobs must create a new queued attempt because previous failed/cancelled attempts should remain immutable audit history.

## Open Questions

None blocking. For the pilot, provider-level cancellation against ComfyUI is out of scope; this slice cancels the control-plane job and prevents local worker state from being overwritten.

## Best Practices Found

No external web search was needed. The best fit is the existing local pattern of explicit mutation endpoints plus idempotent worker skips.

## Conclusion & Recommendation

**Recommended approach:** add explicit `cancel`, `retry`, and `requeue` endpoints for render jobs and publish packages, reuse existing enqueue helpers, and make workers cancellation-aware.

**Key reasons:**
- Matches existing API style and RBAC boundaries.
- Keeps attempts/packages auditable instead of mutating history destructively.
- Gives operators a practical recovery path for stuck queued work and failed/cancelled work.

**Risks of this approach:** provider-level hard cancellation still needs a future ComfyUI adapter enhancement if the provider supports cancellation by provider job id.
