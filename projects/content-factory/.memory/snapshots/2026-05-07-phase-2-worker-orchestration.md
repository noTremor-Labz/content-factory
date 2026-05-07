# Snapshot: Content Factory Phase 2 — Worker Orchestration

**Date:** 2026-05-07
**Scope:** worker orchestration, retry lifecycle, Dramatiq enqueue, attempt response payload

## What Exists Now
- `RenderJob` creation still snapshots workflow inputs and seeds attempt `#1`
- `POST /api/render-jobs` now sends a Dramatiq message to queue `render-jobs` after commit
- Worker actor `process_render_job_message(render_job_id)` delegates to shared orchestration logic
- `process_render_job` loads the job, current queued attempt, and immutable `WorkflowPreset`
- Attempt lifecycle is persisted as:
  - `queued -> running -> succeeded`
  - `queued -> running -> failed -> next queued attempt` while budget remains
  - `queued -> running -> failed` and job `failed` when budget is exhausted
- Terminal render jobs are skipped idempotently
- `JobAttempt.response_payload` persists provider outputs for later packaging/export

## New Data Model
- `job_attempts.response_payload`
  - JSON
  - non-null
  - default empty object
  - exposed through `JobAttemptRead`

## New Worker Surface
- `content_factory_worker.orchestration.RenderExecutor`
- `content_factory_worker.orchestration.RenderExecutionResult`
- `content_factory_worker.orchestration.process_render_job`
- `content_factory_worker.jobs.render.process_render_job_message`
- `content_factory_worker.queue.enqueue_render_job`

## Important Behaviors
- Dramatiq actor has `max_retries=0`; retry policy is owned by the application-level `retry_budget`
- The default actor executor is intentionally unconfigured, so real ComfyUI execution is not faked
- Tests inject executor doubles to verify success/failure lifecycle without requiring Redis or ComfyUI
- API tests use `APP_ENV=test`, which configures a Dramatiq `StubBroker`
- Provider exceptions are converted into failed attempts and continue through the same retry-budget path

## Verification State
- `make lint-api` ✅
- `make typecheck-api` ✅
- `make test-api` ✅
- `make generate-contracts` ✅
- `make lint-web` ✅
- `make typecheck-web` ✅
- `make test-web` ✅

## Next Build Slice
- real/mockable ComfyUI execution adapter
- SSE job status stream
- cockpit queue/job detail UI
- operator `retry`, `cancel`, `requeue`
- FFmpeg packaging/export after render success
