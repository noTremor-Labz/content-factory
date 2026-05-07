# Snapshot: Local Dev Stack Debug

**Date:** 2026-05-07
**Scope:** Environment recovery for `http://localhost:5173/`

## Summary
The apparent hang at `http://localhost:5173/` was caused by the local dev stack not being running. Initially nothing listened on `127.0.0.1:5173`. After Vite was started, the frontend loaded but `/api` proxied requests returned `502 Bad Gateway` because FastAPI and its local dependencies were down.

## Restored Services
- Vite frontend: `127.0.0.1:5173`
- FastAPI API: `0.0.0.0:8000`
- Postgres: `5432` via Docker/Colima
- Redis: `6379` via Docker/Colima
- MinIO API: `9000` via Docker/Colima
- MinIO console: `9001` via Docker/Colima

## Commands Used
- `pnpm --dir apps/web dev --host 127.0.0.1`
- `docker compose -f infra/docker-compose.yml up -d`
- `make migrate-api`
- `make dev-api`
- `PLAYWRIGHT_BASE_URL=http://127.0.0.1:5173 pnpm --dir apps/web test:e2e`

## Verification
- `curl -I -s http://localhost:5173/` returned `200 OK`.
- `curl -s http://localhost:5173/health/ready` returned API readiness with config, database URL, Redis URL, and object storage bucket checks.
- `curl -s http://localhost:5173/api/auth/session` returned `{"detail":"Authentication required"}`, which is expected for an anonymous browser session.
- Playwright cockpit smoke passed: `1 passed`.

## Notes
- The first Alembic migration attempt failed inside the default sandbox with `Operation not permitted` when connecting to local Postgres. The escalated run succeeded.
- The first Playwright attempt failed before reaching the app because Chromium was blocked by macOS sandbox permissions. The escalated run succeeded.
- `/Users/tomasrabi/DEV/shared/port-registry.md` was updated to record the running Content Factory ports.
