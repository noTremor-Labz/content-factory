# Research: Dev Service Watchdog

**Date:** 2026-05-07
**Task size:** M
**Agent:** Codex

---

## Current Architecture

Content Factory local/dev stack currently runs as:

1. Docker Compose infra in `infra/docker-compose.yml`:
   - Postgres on `5432`
   - Redis on `6379`
   - MinIO on `9000` and console on `9001`
2. FastAPI API via `make dev-api` on `8000`
3. Vite cockpit via `make dev-web` on `5173`, proxying `/api` and `/health` to `8000`

Health signals already available:

- API: `GET /health/live`
- API readiness: `GET /health/ready`
- MinIO: `GET /minio/health/live`
- Postgres/Redis Docker healthchecks exist in Compose, but outside Docker the simplest local checks are TCP port checks.

## Affected Areas

| # | File/Module | Why affected |
|---|-------------|--------------|
| 1 | `scripts/dev_watchdog.py` | New local tool that monitors and restarts local/dev services |
| 2 | `apps/worker/tests/test_dev_watchdog.py` | Unit tests for restart behavior without starting real servers |
| 3 | `Makefile` | Add a discoverable `dev-watchdog` target |
| 4 | `README.md` | Document the new command |
| 5 | `.memory/*` | Record spec/plan/handoff/context |

## Codebase Patterns

- Root `Makefile` is the command entrypoint for dev and gates.
- The project currently avoids new runtime dependencies; Python stdlib is enough for a local supervisor.
- Existing local services are bound to reserved Content Factory ports in the shared port registry.
- Tests are Python pytest under `apps/api/tests` and `apps/worker/tests`.

## Risks and Constraints

- This should not become a production process manager. Production deployment/runtime is not yet selected.
- Killing unrelated user processes on ports would be risky. The watchdog should only terminate/restart processes it started itself.
- Docker/Compose operations may require the user's local Docker runtime to be running.
- Health checks must have short timeouts so the loop does not hang.
- The tool should be safe to run in dry-run/once mode for verification.

## Open Questions

- Later: should the worker process be included after direct worker runtime operation is finalized?
- Later: should production use systemd, Docker restart policies, or a cloud supervisor? This slice should not decide that.

## Best Practices Found

- Docker's official docs recommend restart policies for container restart behavior and note Compose supports service-level `restart` policies. This is relevant for future production/runtime hardening, but the current API/Web dev processes are not containerized.
- Docker Compose docs describe `docker compose restart` and service restart behavior; for the existing local infra, `docker compose up -d` remains the safest idempotent "bring it back" command because it creates missing containers as well as starts stopped ones.
- Python official docs for `urllib.request.urlopen` support a timeout argument for bounded health checks.
- Python official subprocess docs support process lifecycle control through `Popen`, `poll`, `terminate`, and `wait`, which fits a small local watchdog.

Sources:
- https://docs.docker.com/engine/containers/start-containers-automatically/
- https://docs.docker.com/reference/compose-file/services/
- https://docs.docker.com/reference/cli/docker/compose/restart/
- https://docs.python.org/3/library/urllib.request.html
- https://docs.python.org/3/library/subprocess.html

## Conclusion & Recommendation

**Recommended approach:** implement a local/dev watchdog script with no new dependencies. It should monitor infra/API/web health, run `docker compose -f infra/docker-compose.yml up -d` when infra is unhealthy, and supervise API/Web processes launched through existing Make targets.

**Key reasons:**
- It solves the user's immediate "поднять при падении" need for the current service shape.
- It avoids silently choosing production infrastructure.
- It is safe: it does not kill unknown processes and can run in `--once --dry-run`.

**Risks of this approach:**
- It only supervises processes started by the watchdog.
- It is not a replacement for future production restart policy/systemd/container runtime work.
- If Docker itself is down, the watchdog can report and retry but cannot repair the Docker runtime.
