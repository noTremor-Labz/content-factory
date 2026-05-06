# Snapshot: Content Factory Phase 1 Control-Plane API

**Date:** 2026-05-06
**Scope:** implementation baseline for `Phase 1 / Domain Model, Auth, And Control-Plane API`

## Files Added
- `alembic.ini`
- `apps/api/alembic/env.py`
- `apps/api/alembic/versions/20260506_0001_control_plane.py`
- `apps/api/src/content_factory_api/database.py`
- `apps/api/src/content_factory_api/modules/*`
- `apps/api/tests/test_auth.py`
- `apps/api/tests/test_control_plane.py`
- `apps/api/tests/test_migrations.py`

## Files Updated
- `apps/api/src/content_factory_api/app.py`
- `apps/api/src/content_factory_api/config.py`
- `apps/api/tests/conftest.py`
- `apps/api/tests/test_health.py`
- `apps/api/tests/test_openapi.py`
- `.env.example`
- `Makefile`
- `README.md`
- `pyproject.toml`
- `packages/contracts/openapi/content-factory.openapi.json`
- `packages/contracts/src/generated/api.ts`
- `.memory/context.md`
- `.memory/sessions/plans/2026-05-06-content-factory-phase-1-control-plane.md`

## Working Baseline
- API has a SQLAlchemy 2 DB layer and Alembic migration baseline.
- Invite-only auth supports bootstrap owner, invites, invite acceptance, login, logout, and current session.
- Cookie sessions store only hashed tokens server-side.
- RBAC gates owner/operator/reviewer/viewer actions.
- Pilot entities exist for brands, avatars, identity packs, assets, content items, review tasks, and audit logs.
- Asset upload initiation returns a real S3-compatible presigned `PUT` URL using local MinIO defaults.
- Content lifecycle enforces `draft -> planned -> review -> approved | rework`.
- Review decisions update both `ReviewTask` and `ContentItem`.
- Audit logs are written for key auth/domain/review actions.
- OpenAPI and TypeScript contracts include the new control-plane endpoints.

## Verified Commands
- `make install-python BOOTSTRAP_PYTHON=/Users/tomasrabi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3`
- `make install-node`
- `make lint-api`
- `make typecheck-api`
- `make test-api`
- `make generate-contracts`
- `pnpm --dir packages/contracts typecheck`
- `make lint-web`
- `make typecheck-web`
- `make test-web`
- `docker compose -f infra/docker-compose.yml config`
- `make -n migrate-api`

## Next Implementation Slice
- `Phase 1 / Cockpit Shell And Review Queue UI`
- Target areas:
  - protected SPA shell and session bootstrap
  - typed API client from `packages/contracts`
  - brand/avatar/asset/content screens
  - review queue approve/rework flow
  - browser smoke flow for the control-plane loop
