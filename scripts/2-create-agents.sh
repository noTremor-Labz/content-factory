#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck source=/dev/null
source "$ROOT/scripts/load-env.sh"
load_env "$ROOT"

echo "=== Шаг 2: Создание агентов ==="
echo ""

cli() {
  docker compose --profile cli run --rm -T openclaw-cli "$@"
}

model_for() {
  case "$1" in
    launch) echo "anthropic/claude-haiku-4-5" ;;
    lens-tomas) echo "anthropic/claude-opus-4-6" ;;
    *) echo "anthropic/claude-sonnet-4-6" ;;
  esac
}

add_agent() {
  local agent=$1
  local ws="/home/node/.openclaw/workspace-${agent}"
  local model
  model="$(model_for "$agent")"
  cli openclaw agents add "$agent" --non-interactive \
    --workspace "$ws" \
    --model "$model"
}

for agent in director scheduler scout launch; do
  if cli openclaw agents list 2>/dev/null | grep -q "^${agent}$"; then
    echo "[SKIP] $agent уже существует"
  else
    add_agent "$agent"
    echo "[DONE] Агент $agent создан"
  fi
done

for agent in quill-tomas lens-tomas pixel-tomas; do
  if cli openclaw agents list 2>/dev/null | grep -q "^${agent}$"; then
    echo "[SKIP] $agent уже существует"
  else
    add_agent "$agent"
    echo "[DONE] Агент $agent создан"
  fi
done

echo ""
echo "Список агентов:"
cli openclaw agents list

echo ""
echo "=== Шаг 2 завершён ==="
echo "Следующий шаг: bash scripts/3-configure.sh"
