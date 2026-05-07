# Research: ComfyUI Provider Adapter And Live Status

**Date:** 2026-05-07
**Task size:** M
**Agent:** Codex

---

## Current Architecture

Phase 2 already has immutable `WorkflowPreset` records, `RenderJob` / `JobAttempt`
tables, generated API contracts, Dramatiq enqueue, and a worker orchestration loop.
The current worker executor is intentionally unconfigured and always fails, so render
jobs can be queued but cannot reach a real provider-backed result.

The cockpit currently loads brands, assets, avatars, identity packs, content, review
tasks, and audit logs. It does not load workflow presets or render jobs, and there is
no operator view for queued/running render status.

## Affected Areas

| # | File/Module | Why affected |
|---|-------------|--------------|
| 1 | `apps/worker/src/content_factory_worker/jobs/render.py` | Replace unconfigured executor with a settings-driven executor factory. |
| 2 | `apps/worker/src/content_factory_worker/executors/comfyui.py` | Add testable ComfyUI HTTP executor. |
| 3 | `apps/worker/src/content_factory_worker/config.py` | Add provider URL/API key/timeout/poll interval settings. |
| 4 | `apps/api/src/content_factory_api/modules/render.py` | Add SSE status stream on existing render job serialization. |
| 5 | `apps/api/src/content_factory_api/modules/schemas.py` | Add stream event schema for OpenAPI/contracts. |
| 6 | `apps/web/src/shared/api/*` | Add render/workflow types and client calls. |
| 7 | `apps/web/src/features/render/*` | Add cockpit queue/job detail UI. |
| 8 | `apps/web/src/app/*` | Load render data and expose a Render route. |

## Codebase Patterns

- API endpoints are synchronous FastAPI route functions using SQLAlchemy `Session`
  dependencies and Pydantic response schemas.
- API tests use `TestClient` and seeded control-plane flows.
- Worker tests inject fake `RenderExecutor` objects, so provider-specific behavior
  should be unit-tested separately from orchestration.
- Web uses a compact hash-routed cockpit with generated OpenAPI types wrapped by
  `shared/api/types.ts` and a fetch-based `apiClient`.
- UI tests use a local fetch mock rather than a real browser unless smoke coverage is
  explicitly needed.

## Risks and Constraints

- Worker attempts must remain idempotent for terminal jobs.
- A provider adapter must not mark a job succeeded merely because submission succeeded;
  it should wait for a terminal provider state or fail with a retryable error.
- SSE should be useful for live cockpit updates without requiring new DB tables.
- The provider integration must stay optional in local/dev so the app remains usable
  without a running ComfyUI server.
- No raw free-form workflow canvas should be exposed to non-operator users in this slice.

## Open Questions

- Final ComfyUI deployment target is still open. The adapter should support local
  ComfyUI-compatible routes first, with optional API key headers for cloud-like targets.

## Best Practices Found

- ComfyUI server docs state that workflows are submitted through `POST /prompt`, which
  returns `prompt_id` and queue position on success, and that `/history/{prompt_id}`
  exposes prompt history.
- ComfyUI docs list `/ws` for real-time execution messages, but this slice can avoid a
  second async event bridge by polling from the worker and streaming local DB state to
  the cockpit.
- Comfy Cloud docs expose terminal status values (`pending`, `in_progress`, `completed`,
  `failed`, `cancelled`) and WebSocket message types, but mark the Cloud API experimental.

Sources:
- https://docs.comfy.org/development/comfyui-server/comms_routes
- https://docs.comfy.org/development/cloud/api-reference

## Conclusion & Recommendation

**Recommended approach:** implement a settings-driven, synchronous ComfyUI HTTP executor
that submits workflow JSON, polls history/status until terminal or timeout, and persists
the full provider response payload; add an API SSE endpoint that streams serialized
render job snapshots from the database; add a focused cockpit Render route for queue and
job detail.

**Key reasons:** it fits the existing worker lifecycle, keeps provider behavior optional
for local/dev, and gives operators visibility without introducing a new event store.

**Risks of this approach:** long renders occupy a worker process; future scale may need
provider callbacks/WebSocket bridging, but that is not necessary for the pilot slice.
