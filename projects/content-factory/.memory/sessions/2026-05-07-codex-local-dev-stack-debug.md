# Handoff: localhost:5173 Debug — Local Dev Stack Recovery

**Date:** 2026-05-07
**Agent:** Codex
**Phase:** Lightweight bugfix / environment recovery

---

## Goal
Diagnose why `http://localhost:5173/` appeared to hang and restore the local Content Factory cockpit so the browser can load the app and talk to the API through the Vite proxy.

## Approach
Used the Bulletproof lightweight path because this was an environment/debugging task with no product code changes: read current context and latest handoff, inspect port/process state, verify HTTP behavior, start only the missing services, then run a browser smoke gate.

## Done
- [x] Read project context and latest Phase 2 provider/live-status handoff.
- [x] Confirmed no process was listening on `127.0.0.1:5173`; initial `curl` failed with connection refused.
- [x] Started the Vite web dev server with `pnpm --dir apps/web dev --host 127.0.0.1`.
- [x] Confirmed the frontend served `/` with `200 OK`.
- [x] Found the second failure: Vite `/api` proxy returned `502 Bad Gateway` because FastAPI and local infra were not running.
- [x] Started local Docker infra via `docker compose -f infra/docker-compose.yml up -d`.
- [x] Ran `make migrate-api`; first sandboxed run could not connect to local Postgres, escalated run succeeded.
- [x] Started FastAPI via `make dev-api` on port `8000`.
- [x] Verified:
  - `http://localhost:5173/` returns `200 OK`.
  - `http://localhost:5173/health/ready` returns API readiness.
  - `http://localhost:5173/api/auth/session` returns expected `401 Authentication required`.
  - `PLAYWRIGHT_BASE_URL=http://127.0.0.1:5173 pnpm --dir apps/web test:e2e` passed when run outside the sandbox.
- [x] Updated `/Users/tomasrabi/DEV/shared/port-registry.md` to reflect the running Content Factory dev stack.

## Current Problem / Next Step
No active blocker for `localhost:5173`: the cockpit is reachable and the smoke test passes. If the stack is no longer needed, stop the long-running dev processes and Docker services, then update the shared port registry again.

## Key Files
- `.memory/context.md` — current project state and next implementation direction.
- `.memory/sessions/2026-05-07-codex-phase-2-provider-live-status.md` — latest product implementation handoff read before debugging.
- `apps/web/vite.config.ts` — Vite proxy maps `/api` and `/health` to `http://localhost:8000`.
- `infra/docker-compose.yml` — local Postgres/Redis/MinIO services used by the API.
- `Makefile` — local commands for `dev-web`, `dev-api`, and `migrate-api`.
- `/Users/tomasrabi/DEV/shared/port-registry.md` — updated with occupied Content Factory ports.

## Key Decisions Made
- Treated this as a lightweight Bulletproof task, not a new implementation phase, because no app code or architecture changed.
- Kept the dev stack running after verification so the user can immediately open `http://localhost:5173/`.
- Used escalation for Docker, Alembic/Postgres access, FastAPI binding, and Playwright because local macOS/Docker/browser access was blocked by the default sandbox.

## Code2Prompt Snapshot
- **Path:** `.memory/snapshots/2026-05-07-local-dev-stack-debug.md`
- **Generated:** 2026-05-07
- **Scope:** environment/debug snapshot only: commands run, observed failures, ports, and verification results. No application source snapshot was needed because no product code changed.

## Gates Status
- [x] HTTP: `curl -I -s http://localhost:5173/` returned `200 OK`.
- [x] API readiness through Vite proxy: `curl -s http://localhost:5173/health/ready` returned `status: ready`.
- [x] Auth/session behavior: `curl -s http://localhost:5173/api/auth/session` returned expected unauthenticated response.
- [x] Browser smoke: `PLAYWRIGHT_BASE_URL=http://127.0.0.1:5173 pnpm --dir apps/web test:e2e` passed.
- [ ] Lint/typecheck were not rerun because no product code was changed in this debug task.

## Context Note
If context is cleared, read this handoff first, then `.memory/context.md`. The running stack at the time of handoff is: Vite `5173`, FastAPI `8000`, Postgres `5432`, Redis `6379`, MinIO `9000/9001`.
