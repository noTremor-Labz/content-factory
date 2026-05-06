# Context: Content Factory

**Last updated:** 2026-05-06
**Status:** phase 1 in progress / workspace bootstrap complete / domain API next

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
- `Phase 1 / Workspace Bootstrap And Shared Tooling` is now implemented.
- Monorepo structure now exists under `apps/web`, `apps/api`, `apps/worker`, `packages/contracts`, and `infra`.
- Web baseline, FastAPI health API, worker bootstrap, local infra compose, and OpenAPI contract generation are working and verified.
- Domain model, auth/RBAC, asset ingress, and review lifecycle have not been started yet.

## Recent Decisions

- 2026-05-06: Bootstrapped as `custom/minimal` because no stack files existed and the technical stack was not yet chosen.
- 2026-05-06: Preserved `.business/` as hidden, gitignored business memory for this project.
- 2026-05-06: Added project-level `AGENTS.md` and `CLAUDE.md` to point agents to identity, memory, handoffs, and business context.
- 2026-05-06: Generated bootstrap snapshot at `.memory/snapshots/2026-05-06-bootstrap.md`.
- 2026-05-06: Recommended pilot stack recorded in `.memory/decisions/2026-05-06-pilot-stack-react-fastapi-comfyui.md`.
- 2026-05-06: Added bulletproof research, spec, master rollout, and 4 separate phase plans under `.memory/sessions/`.
- 2026-05-06: Implemented the first `Phase 1` slice: monorepo bootstrap, verified web/api/worker baseline, local infra compose, and generated contracts.

## Known Issues

- Auth, RBAC, pilot domain entities, upload flow, and review queue are still unimplemented.
- Compliance requirements for vape/nicotine-adjacent content still need legal review before pilot launch.
- Cloud vendor selection is still open, but the reference topology is now fixed in planning artifacts.

## Environment

- Setup: `pnpm` workspace, Python `.venv` bootstrap, and root `Makefile` commands are now in place.
- `.env.example` now contains local defaults for web/api/worker/storage bootstrap.
- MCP preset: general filesystem/GitHub config in `.mcp.json`.

## Recommended Next Step

Continue `Phase 1 — Foundation And Control Plane` with `Domain Model, Auth, And Control-Plane API` using:
- `.memory/sessions/specs/2026-05-06-content-factory-pilot-implementation-rollout.md`
- `.memory/sessions/plans/2026-05-06-content-factory-phase-1-control-plane.md`

Latest handoff: `.memory/sessions/2026-05-06-codex-phase-1-bootstrap-implementation.md`.
