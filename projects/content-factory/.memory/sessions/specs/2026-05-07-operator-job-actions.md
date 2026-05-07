# Spec: Operator Job Actions

**Date:** 2026-05-07
**Author:** user / Codex continuation
**Task size:** M

---

## Problem

Render jobs and publish packages can be queued, running, failed, or stuck, but operators do not yet have control-plane actions to cancel work, retry failed work, or requeue queued work. This leaves the pilot dependent on database edits or new renders/packages for routine recovery.

## Goal

Add role-gated operator actions for render jobs and publish packages so the cockpit can cancel queued/running work, retry failed/cancelled work, and requeue queued work without breaking auditability or existing worker behavior.

## Scope

### In Scope

- Render job `cancel`, `retry`, and `requeue` API endpoints.
- Publish package `cancel`, `retry`, and `requeue` API endpoints.
- Cancelled status for publish packages.
- Worker safeguards so cancelled render/package work is not processed into success.
- Cockpit action buttons on Render and Export panels.
- API, worker, web tests plus regenerated OpenAPI/TypeScript contracts.

### Out of Scope

- Provider-native cancellation calls to ComfyUI or other render backends.
- FFmpeg media normalization.
- New package attempts table.
- Bulk actions or scheduled automatic cleanup.

## Acceptance Criteria

- [ ] Owners/operators can cancel queued/running render jobs; queued/running attempts become cancelled.
- [ ] Owners/operators can retry failed/cancelled render jobs; a new queued attempt is created and the job is enqueued.
- [ ] Owners/operators can requeue queued render jobs idempotently without creating duplicate queued attempts.
- [ ] Owners/operators can cancel queued/running publish packages.
- [ ] Owners/operators can retry failed/cancelled publish packages; package fields are reset and the package is enqueued.
- [ ] Owners/operators can requeue queued publish packages idempotently.
- [ ] Viewers/reviewers cannot call the mutation endpoints.
- [ ] Workers skip cancelled work and do not overwrite operator cancellation after provider execution.
- [ ] Cockpit exposes only valid actions per current status and refreshes after each action.
- [ ] OpenAPI and generated web contracts include the new routes/status.

## Constraints

- Keep the one-package-per-render-job invariant.
- Keep existing render attempt history intact.
- Use existing Dramatiq enqueue helpers.
- Preserve backwards-compatible response bodies by returning existing `RenderJobRead` and `PublishPackageRead`.
- Keep changes focused on the operator action slice.

## Non-Goals

- No new workflow/provider architecture.
- No schema migration unless required by database structure; status is already stored as string.
- No cloud/vendor decisions.
