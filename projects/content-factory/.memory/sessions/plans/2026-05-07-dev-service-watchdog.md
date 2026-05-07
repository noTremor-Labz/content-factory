# Plan: Dev Service Watchdog

**Spec:** `.memory/sessions/specs/2026-05-07-dev-service-watchdog.md`
**Status:** completed

---

## Challenge Log

**Problem:** local/dev recovery is manual across Docker infra, FastAPI, and Vite. The project needs one safe command that detects failure and brings the stack back.

**Chosen solution:** add a stdlib Python watchdog script that checks existing health signals and supervises only the API/Web processes it starts. Infra recovery remains an idempotent Docker Compose `up -d` command.

**Alternatives considered:**
1. Add Docker restart policies for every service — useful later for containerized services, but API/Web are currently foreground dev processes launched by Make targets.
2. Add systemd/launchd units — too host-specific and silently chooses a deployment model.
3. Write a shell loop — simpler initially, but harder to test safely and less robust for process lifecycle handling.

**Why chosen solution is better:** it directly supports the current repo topology, is testable without starting services, avoids killing user-owned processes, and keeps production runtime decisions open.

### Challenge Loop

1. **Does this solve the problem?**
   - It monitors infra/API/web.
   - It starts unhealthy services with existing project commands.
   - It restarts managed API/Web processes after crashes.
   - It provides safe `--once --dry-run` verification.

2. **Is this the most efficient solution?**
   - No new dependencies.
   - No new ports.
   - No production architecture choice.
   - Uses Make/Docker commands already present in the project.

3. **Is there code for code's sake?**
   - No web UI, DB tables, API endpoints, or worker runtime changes.
   - No generic plugin framework.
   - No arbitrary process killing.

## Problems

| # | Problem | Solution | Status |
|---|---------|----------|--------|
| 1 | Infra can be down | Composite infra checks + `docker compose up -d` recovery | completed |
| 2 | API can be down | API health check + managed `make dev-api` process | completed |
| 3 | Web can be down | Web HTTP check + managed `make dev-web` process | completed |
| 4 | Tool could be unsafe | Add dry-run/once modes and avoid killing unmanaged processes | completed |
| 5 | Behavior could regress | Add unit tests with fake health/process/commands | completed |

## Phases

### Phase 1: Local Watchdog Tool
- **Status:** completed
- **Files:** `scripts/dev_watchdog.py`, `apps/worker/tests/test_dev_watchdog.py`, `Makefile`, `README.md`
- **Changes:** add the watchdog CLI, default service specs, Make target, and docs.
- **TDD:** write tests first for healthy no-op, dry-run recovery, process start, and process restart after crash.
- **Gates:** `make lint-api` ✅ | `make typecheck-api` ✅ | `make test-api` ✅ | `.venv/bin/python scripts/dev_watchdog.py --once --dry-run` ✅ | `make -n dev-watchdog` ✅
- **Impact:** local/dev tooling only; no API/web contracts or data migrations.
- **Prompt for launch:**
  ```text
  Read .memory/sessions/plans/2026-05-07-dev-service-watchdog.md.
  Read spec at .memory/sessions/specs/2026-05-07-dev-service-watchdog.md.
  Implement Phase 1 according to plan. Start with tests.
  Do not modify files outside of:
  - scripts/dev_watchdog.py
  - apps/worker/tests/test_dev_watchdog.py
  - Makefile
  - README.md
  - .memory/context.md and handoff/snapshot artifacts after verification
  After completing:
  1. Self-audit against every acceptance criterion
  2. Verify bugs are real before fixing
  3. Impact analysis for local ports/process safety
  4. Run the phase gates
  ```

## Changelog

| Date | Phase | Changes |
|------|-------|---------|
| 2026-05-07 | planning | Created Bulletproof research/spec/plan for local dev service watchdog |
| 2026-05-07 | local-watchdog-tool | Added stdlib dev watchdog, Make target, README docs, and unit tests |
