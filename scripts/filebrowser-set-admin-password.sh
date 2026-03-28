#!/bin/bash
# Сброс пароля пользователя admin (останавливает контейнер на время записи в Bolt DB).
# Использование: FILEBROWSER_PASSWORD='минимум-12-символов' bash scripts/filebrowser-set-admin-password.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -z "${FILEBROWSER_PASSWORD:-}" ] || [ "${#FILEBROWSER_PASSWORD}" -lt 12 ]; then
  echo "Задай FILEBROWSER_PASSWORD (не короче 12 символов), например:"
  echo "  FILEBROWSER_PASSWORD='мой-длинный-пароль' bash scripts/filebrowser-set-admin-password.sh"
  exit 1
fi

VOL="content-factory_filebrowser-data"
docker compose stop filebrowser
docker run --rm --entrypoint /bin/filebrowser \
  -v "${VOL}:/database" \
  filebrowser/filebrowser:latest \
  users update admin -p "$FILEBROWSER_PASSWORD" -d /database/filebrowser.db
docker compose start filebrowser
echo "✅ Пароль admin обновлён. Логин: admin"
