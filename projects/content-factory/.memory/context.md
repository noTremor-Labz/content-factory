# Context: Content Factory

**Last updated:** 2026-05-07
**Status:** phase 2 complete at code-contract level / dev watchdog added / local FFmpeg binary install still pending / compliance and metrics next

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
- API now exposes `PublishPackage` create/list/detail/download contracts gated by approved content plus succeeded render jobs, with idempotent package creation per render job.
- Worker packaging now creates a ZIP manifest bundle from the successful render attempt payload, stores it through S3-compatible storage, persists package object key/manifest/byte size, and marks missing-output packages failed with explicit errors.
- Web cockpit now has an Export route that lists succeeded approved renders, queues publish packages, shows package status/object keys/errors, and fetches signed download URLs for ready packages.
- OpenAPI and generated TypeScript contracts include publish package schemas and routes.
- API now exposes role-gated operator actions for render jobs:
  - `POST /api/render-jobs/{render_job_id}/cancel`;
  - `POST /api/render-jobs/{render_job_id}/retry`;
  - `POST /api/render-jobs/{render_job_id}/requeue`.
- API now exposes role-gated operator actions for publish packages:
  - `POST /api/publish-packages/{package_id}/cancel`;
  - `POST /api/publish-packages/{package_id}/retry`;
  - `POST /api/publish-packages/{package_id}/requeue`.
- Render retries append a new queued attempt, render requeue is idempotent for queued jobs, and render cancellation marks queued/running attempts cancelled.
- Publish packages now support `cancelled`; package retry resets stale object/manifest/error fields and reuses the one-package-per-render-job row.
- Worker orchestration now refreshes render job/attempt state after provider execution so operator cancellation is not overwritten by late provider completion, and package processing skips cancelled packages.
- Web cockpit Render and Export routes now show status-aware operator action buttons and refresh after each action.
- OpenAPI and generated TypeScript contracts include operator action routes and `PublishPackageStatus.cancelled`.
- Worker publish packaging now downloads same-bucket render video artifacts, runs them through an injectable FFmpeg normalizer, includes normalized `video.mp4` in the ZIP bundle, and records `normalized_artifacts` metadata in the manifest.
- Worker settings now include `FFMPEG_PATH` and `FFMPEG_TIMEOUT_SECONDS`; tests use fake normalizers so local verification does not require a real FFmpeg binary.
- Local/dev service recovery now has `scripts/dev_watchdog.py` and `make dev-watchdog`, monitoring infra/API/web and starting unhealthy parts through existing project commands.
- Local cockpit debugging stack is currently restored and verified:
  - Vite frontend on `127.0.0.1:5173`;
  - FastAPI on `0.0.0.0:8000`;
  - Docker Compose infra on `5432`, `6379`, `9000`, `9001`;
  - dev Postgres migrated through `20260507_0004_publish_packages`;
  - browser smoke passed against `PLAYWRIGHT_BASE_URL=http://127.0.0.1:5173`.

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
- 2026-05-07: Diagnosed `localhost:5173` as an inactive local stack, restored Vite/API/Docker infra, ran migrations, verified `/health/ready`, and passed Playwright smoke on `5173`.
- 2026-05-07: Added Phase 2 publish-package/export slice with `PublishPackage` API/model/migration, worker ZIP manifest packaging, cockpit Export route, regenerated contracts, local dev migration, and browser smoke verification on `5173`.
- 2026-05-07: Added Phase 2 operator job actions with role-gated render/package cancel/retry/requeue endpoints, worker cancellation guards, cockpit action buttons, tests, and regenerated contracts.
- 2026-05-07: Re-ran live Playwright cockpit smoke on `127.0.0.1:5173` after operator action UI changes; smoke passed.
- 2026-05-07: Added Phase 2 FFmpeg media normalization contract with S3 artifact download, ZIP `video.mp4`, manifest `normalized_artifacts`, worker settings, and packaging tests.
- 2026-05-07: Added local dev watchdog with dry-run/once modes, infra/API/web checks, managed API/web restart, Make target, docs, and tests.

## Known Issues

- Local/worker runtime still needs a real `ffmpeg` binary installed before real media packages can become `ready`; without it package processing fails cleanly with an explicit error.
- The dev watchdog is local/dev tooling only and does not replace future production supervision. It only terminates API/web processes it started itself.
- Compliance engine, metrics, and direct package worker runtime operation remain future phases.
- ComfyUI adapter submits the stored workflow definition and persists provider output payloads; richer input-to-node mutation remains a future preset mapping enhancement.
- Publish-package ZIPs now include normalized `video.mp4` when FFmpeg runtime is available; cover-image copying and richer platform-specific media validation remain future enhancements.
- Compliance requirements for vape/nicotine-adjacent content still need legal review before pilot launch.
- Cloud vendor selection is still open, but the reference topology is now fixed in planning artifacts.

## Environment

- Setup: `pnpm` workspace, Python `.venv` bootstrap, root `Makefile`, and Alembic migration command are now in place.
- `.env.example` now contains local defaults for web/api/worker/storage/session/upload bootstrap, with `VITE_API_BASE_URL=/` for same-origin Vite proxy dev, `COMFYUI_*` worker settings for optional provider execution, and `FFMPEG_*` worker settings for media normalization.
- Dev recovery: `make dev-watchdog` runs the local watchdog; `.venv/bin/python scripts/dev_watchdog.py --once --dry-run` checks what it would recover without starting services.
- MCP preset: general filesystem/GitHub config in `.mcp.json`.
- Active local debug stack as of 2026-05-07 12:22 MSK:
  - frontend: `http://127.0.0.1:5173/`;
  - API proxy target: `http://localhost:8000`;
  - infra: Postgres `5432`, Redis `6379`, MinIO `9000/9001`.
  - See `.memory/sessions/2026-05-07-codex-local-dev-stack-debug.md` for the recovery report.
  - On 2026-05-07 this stack was migrated to include `publish_packages` and re-smoke-tested.

## Recommended Next Step

Continue after `Phase 2 / Production Pipeline And Render Integration` with:
- `.memory/sessions/plans/2026-05-06-content-factory-phase-2-production-pipeline.md`
- `.memory/sessions/specs/2026-05-06-content-factory-pilot-implementation-rollout.md`
- `.memory/sessions/plans/2026-05-06-content-factory-rollout-master.md`
- immediate next slice: begin `Phase 3 / Compliance, Metrics, And Economics`, or install/provision `ffmpeg` in the worker runtime if real media-package execution is needed before Phase 3

Latest handoff: `.memory/sessions/2026-05-07-codex-dev-service-watchdog.md`.
