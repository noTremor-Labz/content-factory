#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck source=/dev/null
source "$ROOT/scripts/load-env.sh"
load_env "$ROOT"

echo "=== Шаг 3: Конфигурация ==="
echo ""

if ! command -v envsubst &>/dev/null; then
  echo "❌ Нужна утилита envsubst (gettext)."
  echo "   brew install gettext"
  echo "   и добавь в PATH: /opt/homebrew/opt/gettext/bin (Apple Silicon)"
  exit 1
fi

cli() {
  docker compose --profile cli run --rm -T openclaw-cli "$@"
}

GEN="$(mktemp)"
trap 'rm -f "$GEN"' EXIT
envsubst < "$ROOT/openclaw/openclaw.json" > "$GEN"

# Не затирать весь конфиг: иначе пропадёт gateway (токен, bind) и UI не откроется с хоста (Docker + loopback).
if command -v jq &>/dev/null && [ -f ~/.openclaw/openclaw.json ]; then
  jq -s '.[0] as $old | .[1] as $new |
    $old | .agents = $new.agents | .bindings = $new.bindings | .channels = $new.channels' \
    ~/.openclaw/openclaw.json "$GEN" > ~/.openclaw/openclaw.json.tmp
  mv ~/.openclaw/openclaw.json.tmp ~/.openclaw/openclaw.json
  echo "✅ openclaw.json: обновлены agents/bindings/channels, секция gateway сохранена"
else
  cp "$GEN" ~/.openclaw/openclaw.json
  echo "✅ openclaw.json применён (полная замена; установи jq для безопасного слияния)"
fi

cli openclaw config set gateway.mode local 2>/dev/null || true
cli openclaw config set gateway.bind lan 2>/dev/null || true
echo "✅ gateway.mode=local, gateway.bind=lan (доступ с хоста на :18789 в Docker)"

deploy_soul() {
  local agent=$1
  local src=$2
  local dest="$HOME/.openclaw/workspace-$agent/SOUL.md"
  mkdir -p "$(dirname "$dest")"
  if [ -f "$ROOT/souls/$src" ]; then
    cp "$ROOT/souls/$src" "$dest"
    echo "[DONE] souls/$src → workspace-$agent/SOUL.md"
  else
    echo "[WARN] souls/$src не найден"
  fi
}

deploy_soul "director"    "director.md"
deploy_soul "scheduler"   "scheduler.md"
deploy_soul "scout"       "scout.md"
deploy_soul "quill"       "quill.md"
deploy_soul "lens"                  "lens.md"
deploy_soul "launch"         "launch.md"
deploy_soul "pulse-tomas-tg" "pulse-tomas-tg.md"
deploy_soul "pulse-misha-yt" "pulse-misha-yt.md"
deploy_soul "pulse-yulya-ig" "pulse-yulya-ig.md"
deploy_soul "pulse-nasik-tt" "pulse-nasik-tt.md"
deploy_soul "pixel" "pixel.md"

deploy_style_examples() {
  local blogger
  for blogger in tomas misha yulya nasik; do
    local src="$ROOT/shared/bloggers/$blogger/brand/style-examples.md"
    local dest="$HOME/.openclaw/workspace-quill/shared/bloggers/$blogger/brand/style-examples.md"
    if [ -f "$src" ]; then
      mkdir -p "$(dirname "$dest")"
      cp "$src" "$dest"
      echo "[DONE] shared/bloggers/$blogger/brand/style-examples.md → workspace-quill/"
    else
      echo "[WARN] $src не найден"
    fi
  done
}
deploy_style_examples

# Routing для director
if [ -f "$ROOT/souls/routing-director.md" ]; then
  cp "$ROOT/souls/routing-director.md" "$HOME/.openclaw/workspace-director/ROUTING.md"
  echo "[DONE] souls/routing-director.md → workspace-director/ROUTING.md"
fi

if [ -z "${TELEGRAM_DIRECTOR_BOT_TOKEN:-}" ] || [[ "$TELEGRAM_DIRECTOR_BOT_TOKEN" == "..." ]]; then
  echo ""
  echo "⚠️  TELEGRAM_DIRECTOR_BOT_TOKEN не заполнен — пропускаем подключение Telegram"
  echo "   Заполни в .env и перезапусти scripts/3-configure.sh"
else
  echo ""
  echo "Подключение Telegram к Director..."
  cli openclaw channels add \
    --channel telegram \
    --token "$TELEGRAM_DIRECTOR_BOT_TOKEN"
  echo "✅ Telegram (Director) подключён"
fi

if [ -n "${TELEGRAM_REFERENCES_BOT_TOKEN:-}" ] && [[ "${TELEGRAM_REFERENCES_BOT_TOKEN}" != "..." ]]; then
  echo "✅ TELEGRAM_REFERENCES_BOT_TOKEN задан — укажи токен в Credentials для references-style-examples (отдельно от Director)"
else
  echo "ℹ️  Бот References (референсы → style-examples): BotFather → токен в TELEGRAM_REFERENCES_BOT_TOKEN, импорт references-style-examples.json"
fi

echo ""
echo "Перезапуск Gateway..."
cli openclaw gateway restart 2>/dev/null || docker compose restart openclaw-gateway
sleep 5

echo ""
echo "Запуск Agent Board, telegram-bot, FileBrowser..."
docker compose up -d agent-board telegram-bot filebrowser

echo ""
echo "Ожидание запуска сервисов..."
sleep 10

echo ""
echo "=== Шаг 3 завершён ==="
echo ""
BRAND_SOUL="$ROOT/shared/bloggers/tomas/brand/SOUL.md"
BRAND_VS="$ROOT/shared/bloggers/tomas/brand/visual_style.md"
EXAMPLES="$ROOT/shared/bloggers/tomas/brand/examples"
SOUL_LINES=$(wc -l < "$BRAND_SOUL" 2>/dev/null | tr -d ' ' || echo 0)
EX_COUNT=$(find "$EXAMPLES" -type f ! -name '.gitkeep' 2>/dev/null | wc -l | tr -d ' ')
if [ "${SOUL_LINES:-0}" -lt 12 ] || [ ! -f "$BRAND_VS" ]; then
  echo "⚠️  Дополни бренд tomas:"
  echo "   $BRAND_SOUL"
  echo "   $BRAND_VS"
  echo "   $EXAMPLES/"
elif [ "${EX_COUNT:-0}" -eq 0 ]; then
  echo "✅ SOUL / visual_style есть; при желании добавь примеры постов в $EXAMPLES/"
else
  echo "✅ Бренд tomas: SOUL, visual_style и примеры ($EX_COUNT файлов) на месте"
fi
echo ""
echo "Проверка: bash scripts/validate.sh"
