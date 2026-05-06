# Content Factory

AI-сервис контент-завода для цифровых аватаров, коротких видео, human-in-the-loop production pipeline и аналитического цикла улучшения контента.

## Статус

Проект перешел из чистого planning в раннюю реализацию пилота. Recommended stack зафиксирован, а первый технический срез `Phase 1` уже поднял monorepo bootstrap, web/api/worker baseline, local infra и OpenAPI contract generation.

## Быстрый старт для агента

1. Прочитать `AGENTS.md`.
2. Прочитать `.memory/context.md`.
3. Для бизнес-задач прочитать `.business/INDEX.md`, затем только нужные файлы внутри `.business/`.
4. Перед реализацией нетривиальных задач использовать workflow из `shared/skills/bulletproof/SKILL.md`.

## Структура

- `apps/web/` - React 19 + Vite bootstrap для operator cockpit.
- `apps/api/` - FastAPI control-plane API с config validation и health endpoints.
- `apps/worker/` - Dramatiq worker bootstrap для async/render workloads.
- `packages/contracts/` - OpenAPI-derived typed contracts.
- `infra/` - local Docker Compose baseline для Postgres, Redis и MinIO.
- `.business/` - скрытый бизнес-контекст, не коммитится.
- `.memory/` - рабочая память проекта, решения, handoff-и, snapshots.
- `docs/` - документация.
- `scripts/` - служебные скрипты.

## Команды

- Node install: `pnpm install`
- Python install: `make install-python BOOTSTRAP_PYTHON=/path/to/python3.12`
- Web gates: `make lint-web && make typecheck-web && make test-web`
- API/worker gates: `make lint-api && make typecheck-api && make test-api`
- API migrations: `make migrate-api`
- Contracts: `make generate-contracts`
- Dev servers: `make dev-web` и `make dev-api`

## Web Dev Notes

- `VITE_API_BASE_URL=/` использует same-origin proxy Vite для `/api` и `/health`, чтобы local cockpit работал без отдельной CORS-настройки API.
- Presigned upload URLs на локальный MinIO автоматически проксируются через dev server path `"/__storage_proxy"` для browser upload flow.
