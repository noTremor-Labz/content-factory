#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== Шаг 0: Установка зависимостей ==="
echo ""

if ! command -v docker &>/dev/null; then
  echo "❌ Docker Desktop не найден."
  echo ""
  echo "Установи одним из способов:"
  echo "  brew install --cask docker"
  echo "  или: https://www.docker.com/products/docker-desktop/"
  echo ""
  echo "После установки — открой Docker Desktop и дождись запуска."
  exit 1
fi

if ! docker info &>/dev/null; then
  echo "❌ Docker установлен но не запущен."
  echo "   Открой Docker Desktop и дождись иконки в меню-баре."
  exit 1
fi
echo "✅ Docker Desktop: запущен ($(docker --version))"

SHARED="$ROOT/shared/bloggers/tomas"
mkdir -p "$SHARED/brand/examples"
mkdir -p "$SHARED/jobs"
mkdir -p "$SHARED/published"
echo "✅ Папки shared/ созданы"

mkdir -p ~/.openclaw/workspace
if [[ "$(stat -f '%u' ~/.openclaw 2>/dev/null || echo 0)" != "1000" ]]; then
  echo "⚠️  ~/.openclaw может требовать прав для UID 1000 внутри контейнера."
  echo "   При EACCES: sudo chown -R 1000:$(id -g) ~/.openclaw"
fi
echo "✅ ~/.openclaw подготовлен"

AGENT_BOARD_DIST="$ROOT/agent-board/dist"

if [ -d "$AGENT_BOARD_DIST" ] && [ -f "$AGENT_BOARD_DIST/package.json" ]; then
  echo "✅ Agent Board уже собран — пропускаем"
else
  echo ""
  echo "Сборка Agent Board из GitHub..."
  TMP=$(mktemp -d)
  git clone https://github.com/quentintou/agent-board.git "$TMP"
  (cd "$TMP" && npm install && npm run build)
  mkdir -p "$ROOT/agent-board"
  cp -r "$TMP/dist"      "$ROOT/agent-board/"
  cp -r "$TMP/dashboard" "$ROOT/agent-board/"
  cp -r "$TMP/templates" "$ROOT/agent-board/dist/"
  cp    "$TMP/package.json" "$ROOT/agent-board/dist/"
  (cd "$ROOT/agent-board/dist" && npm install --production)
  rm -rf "$TMP"
  echo "✅ Agent Board собран → agent-board/dist/"
fi

if [ ! -f "$ROOT/.env" ]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo ""
  echo "⚠️  Создан .env из .env.example"
  echo "   Заполни обязательные поля перед следующим шагом:"
  echo "   - OPENROUTER_API_KEY (или TOGETHER_API_KEY / COMMONSTACK_API_KEY для маркетплейсов)"
  echo "   - TELEGRAM_BOT_TOKEN"
  echo "   - TELEGRAM_OWNER_ID"
  echo "   - OPENCLAW_CONFIG_DIR, OPENCLAW_WORKSPACE_DIR (путь ~/.openclaw)"
  echo "   - HOST_SHARED_PATH, HOST_AGENT_BOARD_PATH (абсолютные пути к этому репо)"
else
  echo "✅ .env существует"
fi

echo ""
echo "=== Шаг 0 завершён ==="
echo "Следующий шаг: bash scripts/1-openclaw-setup.sh"
