#!/bin/bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck source=/dev/null
source "$ROOT/scripts/load-env.sh"
load_env "$ROOT"

PASS=0
FAIL=0

ok()   { echo "✅ $1"; PASS=$((PASS + 1)); }
fail() { echo "❌ $1"; FAIL=$((FAIL + 1)); }

echo "=== Content Factory — Проверка стека ==="
echo ""

docker ps --format '{{.Names}}' | grep -q '^openclaw-gateway$' && ok "openclaw-gateway: running" || fail "openclaw-gateway: not running"
docker ps --format '{{.Names}}' | grep -q '^agent-board$'      && ok "agent-board: running"      || fail "agent-board: not running"
docker ps --format '{{.Names}}' | grep -q '^n8n$'              && ok "n8n: running"              || fail "n8n: not running"
docker ps --format '{{.Names}}' | grep -q '^filebrowser$'      && ok "filebrowser: running"      || fail "filebrowser: not running"

# С хоста иногда пустой ответ на :18789 (Docker Desktop) — проверяем из контейнера gateway
if docker exec openclaw-gateway curl -fsS http://127.0.0.1:18789/healthz &>/dev/null; then
  ok "OpenClaw Gateway: /healthz OK (из контейнера)"
else
  fail "OpenClaw Gateway: /healthz FAIL"
fi
AB_FIRST="${AGENTBOARD_API_KEYS%%,*}"
AB_KEY="${AB_FIRST%%:*}"
if [ -n "$AB_KEY" ] && curl -fsS -H "X-API-Key: $AB_KEY" http://127.0.0.1:3456/api/health &>/dev/null; then
  ok "Agent Board: /api/health OK"
else
  fail "Agent Board: /api/health FAIL (нужен X-API-Key из AGENTBOARD_API_KEYS)"
fi
curl -fsS http://127.0.0.1:5678/healthz &>/dev/null    && ok "n8n: /healthz OK"             || fail "n8n: /healthz FAIL"
curl -fsS http://127.0.0.1:8080 &>/dev/null            && ok "FileBrowser: responding"      || fail "FileBrowser: not responding"

AGENT_LINES=$(docker compose --profile cli run --rm -T openclaw-cli openclaw agents list 2>/dev/null | sed '/^\s*$/d' | wc -l | tr -d ' ')
if [ "${AGENT_LINES:-0}" -ge 7 ] 2>/dev/null; then
  ok "Агенты: $AGENT_LINES строк в списке (ожидается ≥7)"
else
  fail "Агенты: мало строк в списке ($AGENT_LINES), ожидалось ≥7"
fi

for agent in director scheduler scout quill-tomas lens-tomas pixel-tomas launch; do
  SOUL="$HOME/.openclaw/workspace-$agent/SOUL.md"
  [ -f "$SOUL" ] && ok "SOUL.md: $agent" || fail "SOUL.md: $agent — не найден"
done

[ -d "$ROOT/shared/bloggers/tomas/brand" ] && ok "shared/tomas/brand/" || fail "shared/tomas/brand/"
[ -d "$ROOT/shared/bloggers/tomas/jobs" ]  && ok "shared/tomas/jobs/"  || fail "shared/tomas/jobs/"

[ -n "${ANTHROPIC_API_KEY:-}" ]   && ok ".env: ANTHROPIC_API_KEY"   || fail ".env: ANTHROPIC_API_KEY пустой"
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  ok ".env: TELEGRAM_BOT_TOKEN"
else
  echo "⚠️  TELEGRAM_BOT_TOKEN пустой — бот Director не подключён (добавь в .env и bash scripts/3-configure.sh)"
fi

echo ""
echo "Результат: $PASS ✅  $FAIL ❌"
echo ""

if [ "$FAIL" -eq 0 ]; then
  echo "✅ Всё готово!"
  echo ""
  if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
    echo "Ручной тест — напиши в Telegram-бота:"
    echo "  'тема: тренды осени 2026 | платформа: telegram | формат: пост'"
    echo ""
  fi
  echo "Интерфейсы:"
  echo "  OpenClaw UI:  http://127.0.0.1:18789"
  echo "  Agent Board:  http://127.0.0.1:3456"
  echo "  n8n:          http://127.0.0.1:5678"
  echo "  FileBrowser:  http://127.0.0.1:8080"
else
  echo "❌ Исправь ошибки выше."
  echo "   Логи: docker compose logs [service-name]"
fi
