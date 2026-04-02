# content-factory — гайд для агента

## Точка входа: n8n после clone / git pull

Workflow хранятся в **БД n8n** (volume Docker), а не подхватываются из git автоматически. После обновления репозитория на новой или существующей машине **синхронизируй** workflow из JSON в репо, иначе в UI останется старая версия.

**Когда:** первый деплой, после `git pull`, если менялись `workflows.json`, `n8n-export-approval-send.json` или `n8n-export-telegram-router.json`.

**Команды** (из корня репозитория `content-factory`, контейнер n8n должен быть запущен, имя контейнера — `n8n`):

```bash
docker cp n8n-export-approval-send.json n8n:/tmp/approval-send.json
docker cp n8n-export-telegram-router.json n8n:/tmp/telegram-router.json
docker exec n8n n8n import:workflow --input=/tmp/approval-send.json
docker exec n8n n8n import:workflow --input=/tmp/telegram-router.json
docker exec n8n n8n publish:workflow --id=4lq3sy9j6qlzH99W
docker exec n8n n8n publish:workflow --id=TwB0v8AOQ8CQmJCg
docker restart n8n
```

Идентификаторы workflow: `approval-send` → `4lq3sy9j6qlzH99W`, `telegram-router` → `TwB0v8AOQ8CQmJCg`. Полный дамп всех workflow — файл `workflows.json` в корне (массив; при необходимости импорт отдельных workflow удобнее через `n8n-export-*.json`).

**Проверка:**

```bash
bash scripts/verify-approval-media.sh
```

Полный сценарий с `approve_a` и `published.lock`:

```bash
VERIFY_ROUTER=1 bash scripts/verify-approval-media.sh
```

## Согласование в Telegram (approval-send / telegram-router)

- После отправки поста на согласование workflow **approval-send** пишет состояние в  
  `shared/bloggers/{blogger}/jobs/{job_id}/job-state.json`: `approve_text_message_id`, `approve_media_message_ids` (альбом/одно фото), `approval_ui_kind` (`album` | `single_photo` | `text_only`), `status`.
- Кнопки: **Опубликовать** (`approve_*` / `approve_a` / `approve_b`), **Правки** (`revise_{job_id}`), **Отклонить** (`reject_*`). Обработка колбэков и следующего сообщения редактора — **telegram-router** (тот же URL webhook, что настроен у бота).
- Режим «Жду правки»: `status: awaiting_revision`; после текста правок — `revision_requested`, пишется `draft_approved.md` и вызывается Director через `hooks/agent`. Отмена: сообщение `/cancel` восстанавливает клавиатуру (см. workflow).

## Прочее

- Пайплайн контента и роли агентов: каталог `souls/`.
- Секреты и переменные: `.env` (шаблон — `.env.example`), загрузка через `scripts/load-env.sh`.
