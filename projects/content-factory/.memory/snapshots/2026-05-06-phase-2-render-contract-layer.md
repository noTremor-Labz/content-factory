# Snapshot: Content Factory Phase 2 — Render Contract Layer

**Date:** 2026-05-06
**Scope:** workflow presets, provider contracts, render job seed lifecycle

## What Exists Now
- Immutable versioned `WorkflowPreset` entities with auto-incremented `version` per `key`
- Shared provider registry in `content_factory_pipeline.providers`
- API validation for provider contract shape before preset persistence
- `RenderJob` entities that snapshot resolved inputs from domain data at creation time
- `JobAttempt` entities seeded with queued attempt `#1` during render-job creation
- OpenAPI and generated TS contracts updated with new workflow/render endpoints

## New Data Model
- `workflow_presets`
  - key, version, providers, workflow JSON, input mapping, output mapping
- `render_jobs`
  - content item link, preset snapshot (`key`, `version`, providers), input snapshot, retry budget, status
- `job_attempts`
  - per-job attempt number, status, request payload, provider job id, error/timestamps

## New API Surface
- `POST /api/workflow-presets`
- `GET /api/workflow-presets`
- `GET /api/workflow-presets/{workflow_preset_id}`
- `POST /api/render-jobs`
- `GET /api/render-jobs`
- `GET /api/render-jobs/{render_job_id}`

## Important Behaviors
- Creating the same preset `key` again creates a new immutable version instead of mutating the old one
- Invalid ComfyUI-like definitions are rejected before persistence
- Render job creation requires renderable content status and validates `identity_pack_id` ownership when used
- Input mappings resolve from `content_item`, `brand`, `avatar`, `identity_pack`, or literals, then persist as `input_snapshot`

## Verification State
- `make lint-api` ✅
- `make typecheck-api` ✅
- `make test-api` ✅
- `make generate-contracts` ✅

## Next Build Slice
- worker orchestration for queued jobs
- retries/timeouts/idempotency
- live status transport (SSE)
- UI for queue/job detail
