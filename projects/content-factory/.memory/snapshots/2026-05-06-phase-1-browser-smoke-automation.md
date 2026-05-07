# Snapshot: Content Factory Phase 1 Browser Smoke Automation

**Date:** 2026-05-06
**Scope:** closing Phase 1 with repeatable real-browser smoke coverage

## Files Added / Expanded
- `apps/web/e2e/cockpit.smoke.e2e.ts`
- `apps/web/playwright.config.ts`
- `apps/web/package.json`
- `apps/web/tsconfig.node.json`
- `package.json`
- `Makefile`
- `.gitignore`

## Working Baseline
- Browser smoke is now automated with Playwright against the live local API/storage stack.
- The smoke scenario covers `login/bootstrap -> create brand -> upload asset -> create avatar -> create identity pack -> create content -> plan -> send to review -> approve -> audit`.
- The test is resilient to reruns on a dirty database by using unique names and a `login -> bootstrap owner` auth fallback.
- The earlier in-app browser limitation on `input[type=file]` and `datetime-local` is no longer a blocker for repo-level verification because Playwright drives those controls directly.

## Verified Commands
- `make lint-web`
- `make typecheck-web`
- `make test-web`
- `make test-web-e2e`
- `make test-api`

## Remaining Gap
- Render pipeline, compliance engine, metrics, and publish package export remain future phases.
- Legal/compliance review for vape/nicotine-adjacent content is still pending before pilot launch.
