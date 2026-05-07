# Spec: Dev Service Watchdog

**Date:** 2026-05-07
**Author:** Tomas + Codex
**Task size:** M

---

## Problem

The local Content Factory service stack can stop or crash during development, and recovery currently requires manual checks and separate commands for Docker infra, API, and web. There is no single project tool that watches the stack and brings failed parts back up.

## Goal

Provide a local/dev watchdog command that monitors the Content Factory stack and automatically starts or restarts unhealthy services using the existing project commands.

## Scope

### In Scope

- Add a Python stdlib-only watchdog tool for local/dev use.
- Monitor Docker infra through TCP/HTTP checks for Postgres, Redis, and MinIO.
- Monitor API through `http://127.0.0.1:8000/health/ready`.
- Monitor web cockpit through `http://127.0.0.1:5173/`.
- Bring infra back with `docker compose -f infra/docker-compose.yml up -d`.
- Start/restart API with `make dev-api`.
- Start/restart web with `make dev-web`.
- Support `--once` and `--dry-run` modes for safe verification.
- Log managed process output under `.logs/watchdog/`.
- Add tests for health failure and restart behavior without launching real services.
- Add a `make dev-watchdog` target and README usage note.

### Out of Scope (not doing)

- Production deployment supervision.
- systemd, launchd, Kubernetes, or cloud watchdog configuration.
- Killing arbitrary processes that the watchdog did not start.
- Worker process supervision before direct worker runtime operation is finalized.
- Port registry mutation; this tool uses already allocated Content Factory ports.

## Acceptance Criteria

- [ ] `make dev-watchdog` starts the watchdog tool.
- [ ] `scripts/dev_watchdog.py --once --dry-run` runs without starting real services and reports intended actions.
- [ ] When infra checks fail, the watchdog schedules the Docker Compose `up -d` recovery command.
- [ ] When API/web checks fail, the watchdog starts the matching Make target as a managed process.
- [ ] If a managed API/web process exits and the health check remains failed, the watchdog starts it again.
- [ ] The watchdog does not terminate processes it did not start itself.
- [ ] Unit tests cover dry-run, one-shot command recovery, process restart after crash, and healthy no-op behavior.
- [ ] Project gates pass: `make lint-api`, `make typecheck-api`, `make test-api`.

## Constraints

- Use only Python standard library.
- Keep health check timeouts short.
- Use argument lists for subprocess commands, not shell strings.
- Keep the tool local/dev-scoped until production runtime is explicitly chosen.
- Do not bind new ports.

## Non-Goals

- A full observability stack.
- Persistent daemon installation.
- Restart policies for production containers.
- Worker queue supervision.
