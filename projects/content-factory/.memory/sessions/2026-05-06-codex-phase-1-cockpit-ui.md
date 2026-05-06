# Handoff: Content Factory Phase 1 — Cockpit UI

**Date:** 2026-05-06
**Agent:** Codex
**Phase:** implementation / phase-1-cockpit-ui

---

## Goal
Продолжить `Phase 1` после control-plane API и собрать первый рабочий operator cockpit: protected shell, session bootstrap, typed API client, asset/avatar/content/review screens и audit feed поверх уже существующего backend.

## Approach
Вместо добавления новых тяжёлых frontend-зависимостей cockpit собран на текущем `React 19 + Vite` baseline, с hash-based SPA navigation, typed `fetch` client из generated contracts и component/integration tests на основные lifecycle-переходы. Для локальной работы браузера добавлен Vite proxy для API и MinIO upload flow.

## Done
- [x] Реализован auth entry с `login`, `bootstrap owner`, `accept invite`
- [x] Реализован protected cockpit shell с overview и hash navigation
- [x] Подключен typed API client поверх `packages/contracts`
- [x] Реализованы brand create и asset upload/finalize UI
- [x] Реализованы avatar create и identity-pack create/list UI
- [x] Реализованы content create, plan, submit-review UI
- [x] Реализованы review queue approve/rework actions
- [x] Реализован audit feed UI с RBAC-aware behavior
- [x] Добавлен backend `GET /api/avatars/{avatar_id}/identity-packs` + regenerated contracts
- [x] Добавлены web integration tests на flow `bootstrap/login -> brand -> asset -> avatar -> identity pack -> content -> review -> approve`
- [ ] Browser E2E smoke через Playwright или browser automation пока не добавлен

## Key Files
- `apps/web/src/app/App.tsx`
- `apps/web/src/app/App.css`
- `apps/web/src/app/App.test.tsx`
- `apps/web/src/features/*`
- `apps/web/src/shared/api/*`
- `apps/web/vite.config.ts`
- `apps/api/src/content_factory_api/modules/avatars.py`
- `apps/api/src/content_factory_api/modules/schemas.py`
- `apps/api/tests/test_control_plane.py`
- `packages/contracts/openapi/content-factory.openapi.json`
- `packages/contracts/src/generated/api.ts`

## Verification
- [x] `pnpm --dir apps/web test --run`
- [x] `pnpm --dir apps/web typecheck`
- [x] `pnpm --dir apps/web lint`
- [x] `make lint-api`
- [x] `make typecheck-api`
- [x] `make test-api`
- [x] `pnpm --dir packages/contracts typecheck`

## Current Problem / Next Step
Следующий логичный шаг — завершить этот UI slice browser-level smoke проверкой:
1. поднять local infra + API + web;
2. прогнать сценарий `login/bootstrap -> create brand -> upload asset -> create avatar -> create content -> plan -> send to review -> approve` в реальном браузере;
3. после этого закрыть `Phase 1` и переходить к render/compliance phase.

## Snapshot
- **Path:** `.memory/snapshots/2026-05-06-phase-1-cockpit-ui.md`
- **Generated:** 2026-05-06
- **Scope:** cockpit shell, auth/session bootstrap, asset/avatar/content/review UI, identity-pack list contract, dev proxy behavior

## Context Note
> Если контекст очистится, сначала прочитай этот handoff, затем snapshot, затем `.memory/context.md`, затем phase-1 plan.
