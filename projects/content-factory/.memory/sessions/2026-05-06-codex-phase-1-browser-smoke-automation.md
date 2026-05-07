# Handoff: Content Factory Phase 1 — Browser Smoke Automation

**Date:** 2026-05-06
**Agent:** Codex
**Phase:** implementation / phase-1-browser-smoke-automation

---

## Goal
Закрыть `Phase 1` не только функциональной реализацией cockpit UI, но и повторяемым browser-level smoke на живых local API/storage, чтобы phase можно было считать завершённой без ручной двусмысленности.

## Approach
Сначала был поднят реальный local stack (`postgres`, `redis`, `minio`, `api`, `web`) и пройден живой операторский сценарий. В процессе стало ясно, что in-app browser runtime ограничен на `input[type=file]` и `datetime-local`, поэтому для устойчивого gate в репозиторий добавлен Playwright smoke с уникальными test entities, fallback `login -> bootstrap owner`, и реальной проверкой upload/plan/review/audit поверх live local services.

## Done
- [x] Поднят local infra stack и прогнаны миграции для live smoke
- [x] Пройден живой cockpit flow до `approve`, включая проверку audit trail
- [x] Подтверждено, что ограничения были в in-app browser runtime, а не в самом product flow
- [x] Добавлен `@playwright/test` в `apps/web`
- [x] Добавлены `apps/web/playwright.config.ts` и `apps/web/e2e/cockpit.smoke.e2e.ts`
- [x] Добавлены команды `pnpm --dir apps/web test:e2e`, root `test-web-e2e`, и `make test-web-e2e`
- [x] Обновлены `.gitignore` и `apps/web/tsconfig.node.json` для e2e артефактов и typecheck
- [x] Закрыт phase-1 gate реальным browser smoke: `login/bootstrap -> create brand -> upload asset -> create avatar -> create identity pack -> create content -> plan -> send to review -> approve -> audit`

## Key Files
- `apps/web/e2e/cockpit.smoke.e2e.ts`
- `apps/web/playwright.config.ts`
- `apps/web/package.json`
- `apps/web/tsconfig.node.json`
- `package.json`
- `Makefile`
- `.gitignore`

## Verification
- [x] `make lint-web`
- [x] `make typecheck-web`
- [x] `make test-web`
- [x] `make test-web-e2e`
- [x] `make test-api`

## Result
- `Phase 1 / Foundation And Control Plane` теперь можно считать завершённой.
- Cockpit lifecycle подтверждён не только моками, но и реальным браузерным прогоном на live local stack.
- E2E smoke устойчив к dirty state: использует уникальные names/prefixes и сначала пробует `login`, затем fallback на `bootstrap owner`.

## Next Step
Переходить к `Phase 2 / Production Pipeline And Render Integration` по:
- `.memory/sessions/plans/2026-05-06-content-factory-phase-2-production-pipeline.md`
- `.memory/sessions/plans/2026-05-06-content-factory-rollout-master.md`

## Snapshot
- **Path:** `.memory/snapshots/2026-05-06-phase-1-browser-smoke-automation.md`
- **Generated:** 2026-05-06
- **Scope:** Playwright smoke gate, live cockpit verification, phase-1 closure

## Context Note
> Если контекст очистится, сначала прочитай этот handoff, затем snapshot, затем `.memory/context.md`, затем phase-2 production-pipeline plan.
