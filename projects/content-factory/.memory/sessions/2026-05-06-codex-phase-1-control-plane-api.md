# Handoff: Content Factory Phase 1 — Control-Plane API

**Date:** 2026-05-06
**Agent:** Codex
**Phase:** implementation / phase-1-control-plane-api

---

## Goal
Продолжить `Phase 1` после bootstrap-среза и реализовать pilot domain/control-plane API: auth/RBAC, основные сущности, upload contract, review lifecycle, audit trail, миграции и обновленные OpenAPI contracts.

## Approach
Сделан один законченный backend slice без frontend UI: FastAPI + SQLAlchemy 2 + Alembic, cookie sessions, invite-only user onboarding и небольшая pilot-specific state machine для контента. Multi-tenant и render/compliance pipeline намеренно не добавлялись.

## Done
- [x] Добавлен SQLAlchemy session/engine слой и Alembic baseline.
- [x] Добавлены модели `User`, `Invite`, `UserSession`, `Brand`, `Avatar`, `IdentityPack`, `Asset`, `ContentItem`, `ReviewTask`, `AuditLog`.
- [x] Реализованы auth endpoints: bootstrap owner, invite create/accept, login/logout, current session.
- [x] Реализован RBAC для owner/operator/reviewer/viewer.
- [x] Реализованы users/brands/avatars/identity-packs/assets/content/review/audit routers.
- [x] Реализован S3-compatible presigned `PUT` upload initiation через boto3 и finalize endpoint.
- [x] Реализован lifecycle `draft -> planned -> review -> approved | rework`.
- [x] Добавлены audit entries для auth/domain/review действий.
- [x] Сгенерированы OpenAPI JSON и TypeScript contracts.
- [ ] Cockpit/review frontend UI.
- [ ] Browser E2E flow `login -> upload -> create content -> review`.

## Key Files
- `apps/api/src/content_factory_api/database.py`
- `apps/api/src/content_factory_api/modules/*`
- `apps/api/alembic/versions/20260506_0001_control_plane.py`
- `apps/api/tests/test_auth.py`
- `apps/api/tests/test_control_plane.py`
- `apps/api/tests/test_migrations.py`
- `packages/contracts/openapi/content-factory.openapi.json`
- `packages/contracts/src/generated/api.ts`

## Verification
- [x] `make lint-api`
- [x] `make typecheck-api`
- [x] `make test-api`
- [x] `make generate-contracts`
- [x] `pnpm --dir packages/contracts typecheck`
- [x] `make lint-web`
- [x] `make typecheck-web`
- [x] `make test-web`
- [x] `docker compose -f infra/docker-compose.yml config`
- [x] `make -n migrate-api`

## Snapshot
- **Path:** `.memory/snapshots/2026-05-06-phase-1-control-plane-api.md`
- **Generated:** 2026-05-06
- **Scope:** domain model, auth/RBAC, control-plane API, migration, contracts

## Next Step
Continue `Phase 1 / Cockpit Shell And Review Queue UI` using the regenerated contracts. Start with protected session bootstrap, API client wiring, cockpit navigation, asset upload UI, content create/plan/submit review, and review approve/rework screens.
