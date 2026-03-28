#!/bin/bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "⚠️  Сброс: очистка jobs/ и перезапуск контейнеров"
read -r -p "Продолжить? (y/N): " c
[ "$c" != "y" ] && exit 0

cd "$ROOT"
rm -rf "$ROOT/shared/bloggers/tomas/jobs/"*
touch "$ROOT/shared/bloggers/tomas/jobs/.gitkeep" 2>/dev/null || true
echo "[DONE] jobs/ очищены"

docker compose restart
echo "[DONE] Контейнеры перезапущены"

echo "✅ Сброс завершён"
