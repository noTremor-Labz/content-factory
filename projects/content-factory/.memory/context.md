# Context: Content Factory

**Last updated:** 2026-05-07
**Status:** phase 2 in progress / provider adapter and live status slice complete / packaging-export next

## Stack

- Type: custom/minimal bootstrap with implementation planning complete
- Frontend (recommended): `React 19 + TypeScript + Vite + TanStack Router + TanStack Query + Tailwind + shadcn/Radix`
- API (recommended): `Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic`
- Workers (recommended): `Python 3.12 + Dramatiq + Redis`
- Data plane (recommended): `PostgreSQL + Redis + S3-compatible object storage`
- Render plane (recommended): `ComfyUI-compatible backend + FFmpeg`

## Architecture

Recommended product shape is now documented and approved as the working implementation direction for the pilot:

- monorepo with `apps/web`, `apps/api`, `apps/worker`, `packages/contracts`;
- control plane separated from render plane;
- ComfyUI retained as workflow/render backend, not rewritten;
- human review and compliance treated as first-class lifecycle gates;
- pilot optimized for one primary avatar, manual publishing, Reels and YouTube Shorts.

See:
- `.memory/decisions/2026-05-06-pilot-stack-react-fastapi-comfyui.md`
- `.memory/sessions/specs/2026-05-06-content-factory-pilot-implementation-rollout.md`
- `.memory/sessions/plans/2026-05-06-content-factory-rollout-master.md`

## Current Work

- Project bootstrap and planning artifacts remain intact.
- `Phase 1 / Workspace Bootstrap And Shared Tooling` is complete.
- `Phase 1 / Domain Model, Auth, And Control-Plane API` is complete.
- `Phase 1 / Cockpit Shell And Review Queue UI` is complete and now covered by real-browser Playwright smoke.
- `Phase 2 / Workflow Presets And Provider Contracts` is now complete.
- Monorepo structure now exists under `apps/web`, `apps/api`, `apps/worker`, `packages/contracts`, and `infra`.
- FastAPI now has SQLAlchemy/Alembic baseline, invite-only auth, cookie sessions, RBAC, pilot domain entities, upload initiation/finalization, content lifecycle, review tasks, and audit logs.
- OpenAPI and generated TypeScript contracts include the control-plane API and identity-pack list endpoint.
- Web cockpit UI now has protected session bootstrap, hash navigation, typed API client wiring, auth/bootstrap/invite forms, brand/asset intake, avatar/identity-pack screens, content lifecycle actions, review approve/rework, and audit view.
- Playwright smoke now covers `login/bootstrap -> create brand -> upload asset -> create avatar -> create identity pack -> create content -> plan -> send to review -> approve -> audit` against live local API/storage.
- API now also exposes immutable versioned `WorkflowPreset` creation/list/detail and queued `RenderJob` creation/detail/list with first-attempt seeding and resolved input snapshots.
- Shared pipeline provider contracts now live in `content_factory_pipeline`, with default `comfyui` / `none` / `ffmpeg` registry reused by API validation and worker tests.
- Worker orchestration now processes queued render attempts through a typed executor contract, persists attempt response payloads, transitions jobs through running/succeeded/failed states, enforces retry budget by queueing follow-up attempts, and skips terminal jobs idempotently.
- Render job creation now enqueues a Dramatiq `render-jobs` message after the database job/attempt is committed.
- Worker now has a settings-driven `ComfyUiRenderExecutor` with local/cloud-compatible HTTP submission, provider status polling, timeout/failure mapping, optional API key support, and persisted provider payloads.
- API now exposes authenticated `GET /api/render-jobs/{render_job_id}/events` SSE snapshots for live render status.
- Web cockpit now has a Render route that loads workflow presets/render jobs, creates render jobs for renderable content, subscribes to selected job SSE updates, and shows attempts/provider payloads.

## Recent Decisions

- 2026-05-06: Bootstrapped as `custom/minimal` because no stack files existed and the technical stack was not yet chosen.
- 2026-05-06: Preserved `.business/` as hidden, gitignored business memory for this project.
- 2026-05-06: Added project-level `AGENTS.md` and `CLAUDE.md` to point agents to identity, memory, handoffs, and business context.
- 2026-05-06: Generated bootstrap snapshot at `.memory/snapshots/2026-05-06-bootstrap.md`.
- 2026-05-06: Recommended pilot stack recorded in `.memory/decisions/2026-05-06-pilot-stack-react-fastapi-comfyui.md`.
- 2026-05-06: Added bulletproof research, spec, master rollout, and 4 separate phase plans under `.memory/sessions/`.
- 2026-05-06: Implemented the first `Phase 1` slice: monorepo bootstrap, verified web/api/worker baseline, local infra compose, and generated contracts.
- 2026-05-06: Implemented the second `Phase 1` slice: SQLAlchemy/Alembic domain model, invite-only auth/RBAC, asset upload contracts, content/review lifecycle, audit logs, and regenerated contracts.
- 2026-05-06: Implemented the cockpit UI slice: protected SPA shell, typed API client, Vite proxy/storage proxy, brand/asset/avatar/content/review/audit screens, identity-pack listing, and mocked cockpit flow tests.
- 2026-05-06: Reconciled phase-1 memory docs after parallel review: corrected Phase 3 file map, removed stale smoke gate, and fixed the clean-state browser smoke sequence.
- 2026-05-06: Closed Phase 1 with Playwright smoke automation, new `make test-web-e2e` gate, and real-browser verification of the cockpit lifecycle on live local infra.
- 2026-05-06: Started Phase 2 by adding shared provider contracts, immutable workflow preset versioning, render job/job attempt tables, new render API routes, and regenerated OpenAPI/contracts.
- 2026-05-07: Added Phase 2 worker orchestration with Dramatiq enqueue, attempt lifecycle processing, retry budget enforcement, response payload persistence, and regenerated contracts.
- 2026-05-07: Added Phase 2 provider/live-status slice with ComfyUI HTTP executor, render job SSE stream, cockpit Render queue/detail UI, and regenerated contracts.

## Known Issues

- Operator retry/cancel/requeue actions, FFmpeg packaging/export, compliance engine, metrics, and publish package export remain future phases.
- ComfyUI adapter submits the stored workflow definition and persists provider output payloads; richer input-to-node mutation remains a future preset mapping enhancement.
- Compliance requirements for vape/nicotine-adjacent content still need legal review before pilot launch.
- Cloud vendor selection is still open, but the reference topology is now fixed in planning artifacts.

## Environment

- Setup: `pnpm` workspace, Python `.venv` bootstrap, root `Makefile`, and Alembic migration command are now in place.
- `.env.example` now contains local defaults for web/api/worker/storage/session/upload bootstrap, with `VITE_API_BASE_URL=/` for same-origin Vite proxy dev and `COMFYUI_*` worker settings for optional provider execution.
- MCP preset: general filesystem/GitHub config in `.mcp.json`.

## Recommended Next Step

Continue `Phase 2 / Production Pipeline And Render Integration` with:
- `.memory/sessions/plans/2026-05-06-content-factory-phase-2-production-pipeline.md`
- `.memory/sessions/specs/2026-05-06-content-factory-pilot-implementation-rollout.md`
- `.memory/sessions/plans/2026-05-06-content-factory-rollout-master.md`
- immediate next slice: operator retry/cancel/requeue actions or FFmpeg publish-package/export pipeline on top of completed render execution/status visibility

Latest handoff: `.memory/sessions/2026-05-07-codex-phase-2-provider-live-status.md`.
