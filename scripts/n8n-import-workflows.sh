#!/usr/bin/env bash
# Импорт всех workflow из n8n/workflows/ в контейнер n8n.
# Пропускает файлы с именем на _ (например _draft-foo.json).
#
# Требования: Docker, контейнер с именем из N8N_CONTAINER (по умолчанию n8n).
# После смены переменных в compose: docker compose up -d n8n --force-recreate
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WF_DIR="$ROOT/n8n/workflows"
CONTAINER="${N8N_CONTAINER:-n8n}"

if ! docker inspect "$CONTAINER" >/dev/null 2>&1; then
  echo "Контейнер «$CONTAINER» не найден. Запусти stack: docker compose up -d" >&2
  exit 1
fi

shopt -s nullglob
for f in "$WF_DIR"/*.json; do
  base=$(basename "$f")
  if [[ "$base" == _* ]]; then
    echo "Пропуск $base"
    continue
  fi
  echo "Импорт $base ..."
  docker cp "$f" "$CONTAINER:/tmp/$base"
  docker exec "$CONTAINER" n8n import:workflow --input="/tmp/$base"
done
echo "Готово."
