# Snapshot: Content Factory Phase 1 Cockpit UI

**Date:** 2026-05-06
**Scope:** protected operator cockpit on top of the control-plane API

## Files Added / Expanded
- `apps/web/src/app/*`
- `apps/web/src/features/auth/*`
- `apps/web/src/features/brands-assets/*`
- `apps/web/src/features/avatars/*`
- `apps/web/src/features/content/*`
- `apps/web/src/features/review/*`
- `apps/web/src/features/audit/*`
- `apps/web/src/shared/api/*`
- `apps/api/src/content_factory_api/modules/avatars.py`
- `apps/api/src/content_factory_api/modules/schemas.py`
- `apps/api/tests/test_control_plane.py`

## Working Baseline
- Anonymous users land in auth gate with `login`, `bootstrap owner`, and `accept invite` flows.
- Authenticated users get a protected cockpit shell with overview, brands/assets, avatars, content, review, and audit screens.
- Asset upload flow performs `initiate -> presigned PUT -> finalize`.
- Identity packs can now be listed per avatar through the API and rendered after refresh.
- Content lifecycle UI supports `draft -> planned -> review -> approved | rework`.
- Review tasks can be approved or sent to rework from the browser UI.
- Local Vite dev proxy handles `/api`, `/health`, and MinIO upload proxying for browser uploads.

## Verified Commands
- `pnpm --dir apps/web test --run`
- `pnpm --dir apps/web typecheck`
- `pnpm --dir apps/web lint`
- `make lint-api`
- `make typecheck-api`
- `make test-api`
- `pnpm --dir packages/contracts typecheck`

## Remaining Gap
- No real-browser E2E smoke yet.
- No render/compliance/metrics UI yet.
