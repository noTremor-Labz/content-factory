# Handoff: Content Factory — Dev Service Watchdog

**Date:** 2026-05-07
**Agent:** Codex
**Phase:** Local/dev recovery tooling slice

---

## Goal

Add a local tool that watches the Content Factory dev stack and brings unhealthy parts back up after a crash or stop.

## Approach

Implemented a stdlib Python watchdog instead of choosing production supervision. It monitors the current local stack ports/health endpoints, runs Docker Compose recovery for infra, and manages only the API/Web processes it starts itself.

## Done

- [x] Created Bulletproof artifacts:
  - `.memory/sessions/research/2026-05-07-dev-service-watchdog.md`
  - `.memory/sessions/specs/2026-05-07-dev-service-watchdog.md`
  - `.memory/sessions/plans/2026-05-07-dev-service-watchdog.md`
- [x] Added `scripts/dev_watchdog.py`.
- [x] Added unit coverage in `apps/worker/tests/test_dev_watchdog.py`.
- [x] Added `make dev-watchdog`.
- [x] Included `scripts` in Python lint/typecheck gates.
- [x] Documented usage in `README.md`.
- [x] Updated `.memory/context.md` and generated a snapshot.

## Current Problem / Next Step

The local watchdog is ready. Use:

```bash
make dev-watchdog
```

For safe inspection without starting anything:

```bash
.venv/bin/python scripts/dev_watchdog.py --once --dry-run
```

Next product slice remains `Phase 3 / Compliance, Metrics, And Economics`, unless real FFmpeg runtime provisioning should happen first.

## Key Files

- `scripts/dev_watchdog.py` — watchdog CLI and recovery logic.
- `apps/worker/tests/test_dev_watchdog.py` — fake health/process tests.
- `Makefile` — `dev-watchdog` target and `scripts` lint/typecheck inclusion.
- `README.md` — usage note.
- `.memory/sessions/specs/2026-05-07-dev-service-watchdog.md` — acceptance criteria.

## Key Decisions Made

- Chose local/dev watchdog scope, not production supervision, because production runtime is not selected yet.
- Chose stdlib Python over shell loop so process lifecycle behavior is testable.
- The watchdog does not kill unknown processes; it only terminates API/Web processes it started itself.
- Worker supervision remains out of scope until direct worker runtime operation is finalized.

## Code2Prompt Snapshot

- **Path:** `.memory/snapshots/2026-05-07-dev-service-watchdog.md`
- **Generated:** 2026-05-07
- **Scope:** watchdog script, watchdog tests, Makefile, README, and Bulletproof artifacts for this slice.

## Gates Status

- [x] Targeted tests: `PYTHONPATH=apps/api/src:apps/worker/src .venv/bin/python -m pytest apps/worker/tests/test_dev_watchdog.py -q` (`5 passed`)
- [x] Dry run: `.venv/bin/python scripts/dev_watchdog.py --once --dry-run`
- [x] Make target check: `make -n dev-watchdog`
- [x] Lint: `make lint-api`
- [x] Type check: `make typecheck-api`
- [x] Tests: `make test-api` (`52 passed`)
- [ ] Security scan: not run; no semgrep installation was added.

## Context Note

> If context is cleared, read this handoff first, then `.memory/snapshots/2026-05-07-dev-service-watchdog.md`.
