#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=/dev/null
source "$ROOT/scripts/load-env.sh"
load_env "$ROOT"

echo "=== Шаг 1: Запуск OpenClaw Gateway ==="
echo ""

if [ -z "${ANTHROPIC_API_KEY:-}" ] || [[ "$ANTHROPIC_API_KEY" == "sk-ant-..." ]]; then
  echo "❌ Нужен реальный ANTHROPIC_API_KEY (не плейсхолдер sk-ant-... из примера)."
  echo "   Файл: $ROOT/.env или .env.local — сохрани в редакторе (Cmd+S), затем повтори скрипт."
  exit 1
fi
if [ "${#ANTHROPIC_API_KEY}" -lt 30 ]; then
  echo "❌ ANTHROPIC_API_KEY слишком короткий (${#ANTHROPIC_API_KEY} символов). Полный ключ из console.anthropic.com — длинная строка."
  exit 1
fi

if [ ! -f ~/.openclaw/openclaw.json ]; then
  echo "Первый запуск — онбординг OpenClaw (без интерактива)..."
  echo ""

  docker compose run --rm -T --no-deps \
    --entrypoint node \
    openclaw-gateway \
    dist/index.js onboard \
    --non-interactive \
    --accept-risk \
    --mode local \
    --no-install-daemon \
    --auth-choice apiKey \
    --anthropic-api-key "$ANTHROPIC_API_KEY" \
    --secret-input-mode plaintext \
    --gateway-bind lan \
    --gateway-port "${OPENCLAW_GATEWAY_PORT:-18789}" \
    --skip-skills \
    --skip-health

  if [ -f ~/.openclaw/.env ]; then
    GENERATED_TOKEN=$(grep '^OPENCLAW_GATEWAY_TOKEN=' ~/.openclaw/.env | cut -d= -f2- || true)
    if [ -n "${GENERATED_TOKEN:-}" ]; then
      if grep -q '^OPENCLAW_GATEWAY_TOKEN=' "$ROOT/.env"; then
        sed -i.bak "s|^OPENCLAW_GATEWAY_TOKEN=.*|OPENCLAW_GATEWAY_TOKEN=$GENERATED_TOKEN|" "$ROOT/.env"
      else
        echo "OPENCLAW_GATEWAY_TOKEN=$GENERATED_TOKEN" >> "$ROOT/.env"
      fi
      echo "✅ Gateway token сохранён в .env"
    fi
  fi

  docker compose run --rm -T --no-deps \
    --entrypoint node \
    openclaw-gateway \
    dist/index.js config set gateway.mode local
  docker compose run --rm -T --no-deps \
    --entrypoint node \
    openclaw-gateway \
    dist/index.js config set gateway.bind lan

else
  echo "✅ ~/.openclaw/openclaw.json существует — онбординг пропускаем"
fi

echo ""
echo "Запуск openclaw-gateway..."
load_env "$ROOT"
docker compose up -d openclaw-gateway

echo ""
echo "Ожидание запуска Gateway (до ~60 секунд)..."
for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:18789/healthz &>/dev/null; then
    echo "✅ Gateway запущен: http://127.0.0.1:18789"
    break
  fi
  sleep 2
done

if ! curl -fsS http://127.0.0.1:18789/healthz &>/dev/null; then
  echo "❌ Gateway не запустился за отведённое время. Проверь логи:"
  echo "   docker compose logs openclaw-gateway"
  exit 1
fi

echo ""
echo "Control UI (если доступен):"
docker compose --profile cli run --rm -T openclaw-cli dashboard --no-open 2>/dev/null || true
echo ""
echo "=== Шаг 1 завершён ==="
echo "Следующий шаг: bash scripts/2-create-agents.sh"
