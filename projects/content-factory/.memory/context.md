# Context: Content Factory

**Last updated:** 2026-05-06
**Status:** phase 1 in progress / cockpit UI implemented / browser smoke next

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
- `Phase 1 / Workspace Bootstrap And Shared Tooling` is implemented.
- `Phase 1 / Domain Model, Auth, And Control-Plane API` is implemented.
- `Phase 1 / Cockpit Shell And Review Queue UI` is functionally implemented, with browser-level smoke automation still pending.
- Monorepo structure now exists under `apps/web`, `apps/api`, `apps/worker`, `packages/contracts`, and `infra`.
- FastAPI now has SQLAlchemy/Alembic baseline, invite-only auth, cookie sessions, RBAC, pilot domain entities, upload initiation/finalization, content lifecycle, review tasks, and audit logs.
- OpenAPI and generated TypeScript contracts include the control-plane API and identity-pack list endpoint.
- Web cockpit UI now has protected session bootstrap, hash navigation, typed API client wiring, auth/bootstrap/invite forms, brand/asset intake, avatar/identity-pack screens, content lifecycle actions, review approve/rework, and audit view.

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

## Known Issues

- Browser E2E smoke flow against real local API/storage is still not automated; current cockpit flow is covered by mocked Vitest component/integration tests.
- Render pipeline, compliance engine, metrics, and publish package export remain future phases.
- Compliance requirements for vape/nicotine-adjacent content still need legal review before pilot launch.
- Cloud vendor selection is still open, but the reference topology is now fixed in planning artifacts.

## Environment

- Setup: `pnpm` workspace, Python `.venv` bootstrap, root `Makefile`, and Alembic migration command are now in place.
- `.env.example` now contains local defaults for web/api/worker/storage/session/upload bootstrap, with `VITE_API_BASE_URL=/` for same-origin Vite proxy dev.
- MCP preset: general filesystem/GitHub config in `.mcp.json`.

## Recommended Next Step

Finish `Phase 1` with browser-level smoke coverage for the implemented cockpit UI using `login/bootstrap -> create brand -> upload asset -> create avatar -> create content -> plan -> send to review -> approve`, then continue with render/compliance groundwork using:
- `.memory/sessions/specs/2026-05-06-content-factory-pilot-implementation-rollout.md`
- `.memory/sessions/plans/2026-05-06-content-factory-rollout-master.md`

Latest handoff: `.memory/sessions/2026-05-06-codex-phase-1-memory-sync-after-parallel-review.md`.
