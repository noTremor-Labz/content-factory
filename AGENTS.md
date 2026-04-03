# content-factory — гайд для агента

## Пайплайн и автоматизация

Вместо legacy-сервиса используется `telegram_bot/` — Python-сервис на `aiogram 3.x` + `APScheduler`.

Компоненты:
- `scheduler.py` — cron-триггеры (daily queue, trend parsing, stuck-task check)
- `approval.py` — отправка поста на согласование в Telegram с фото и кнопками
- `router.py` — обработка callback-кнопок (approve / revise / reject)
- `watcher.py` — файловый watcher на `ready.md` (триггерит отправку на approval)
- `publisher.py` — watcher на `published.flag` (логирование + уведомление)
- `sheets.py` — запись в Google Sheets через service account JSON
- `alerter.py` — алерты о зависших job

## Прочее

- Пайплайн контента и роли агентов: каталог `souls/`.
- Секреты и переменные: `.env` (шаблон — `.env.example`), загрузка через `scripts/load-env.sh`.
