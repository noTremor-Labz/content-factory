#!/usr/bin/env bash
# Интеграционный прогон content-factory: инфраструктура, фикстура job, опционально Lens / approval / Pixel.
# Запуск из корня репозитория: bash scripts/test-workflow.sh [опции]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck source=/dev/null
source "$ROOT/scripts/load-env.sh"
load_env "$ROOT"

GATEWAY_URL="${OPENCLAW_GATEWAY_URL:-http://127.0.0.1:${OPENCLAW_GATEWAY_PORT:-18789}}"
N8N_URL="${N8N_URL:-http://127.0.0.1:5678}"
BLOGGER="${BLOGGER:-tomas-food}"
PLATFORM="${PLATFORM:-tg}"

RUN_LENS=0
RUN_APPROVAL=0
RUN_PIXEL=0
SMOKE_ONLY=0

usage() {
  cat <<EOF
Usage: bash scripts/test-workflow.sh [опции]

  (без флагов)   health + создать тестовый job + опционально шаги по флагам
  --smoke-only   только curl health (gateway), без LLM и без n8n
  --lens         три вызова openclaw agent --agent lens (стоит денег / время)
  --approval     POST на webhook approval-send (нужен n8n; сообщение в TG владельцу)
  --pixel        python3 shared/scripts/pixel_upload.py (нужны FAL/R2 в .env)

Переменные: BLOGGER (default tomas-food), PLATFORM (default tg),
  OPENCLAW_GATEWAY_URL, N8N_URL

Примеры:
  bash scripts/test-workflow.sh --smoke-only
  bash scripts/test-workflow.sh --approval
  bash scripts/test-workflow.sh --lens
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --smoke-only) SMOKE_ONLY=1 ;;
    --lens) RUN_LENS=1 ;;
    --approval) RUN_APPROVAL=1 ;;
    --pixel) RUN_PIXEL=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Неизвестный аргумент: $1"; usage; exit 1 ;;
  esac
  shift
done

JOB_ID="wf-test-$(date +%Y%m%d-%H%M%S)"
JOB_DIR="$ROOT/shared/bloggers/$BLOGGER/jobs/$JOB_ID"
SESSION_KEY="lens-job-$JOB_ID"

say() { printf '\n=== %s ===\n' "$*"; }

say "Job: $JOB_ID → $JOB_DIR"
mkdir -p "$JOB_DIR"

cat > "$JOB_DIR/research.md" <<EOF
# Research (test-workflow)

Кратко: тестовый прогон пайплайна. Тема — пищевая индустрия и автоматизация.
EOF

cat > "$JOB_DIR/draft_v1.md" <<'EOF'
Тестовый черновик для workflow.

Проблема: без конвейера контент тормозит. Решение: агенты + ревью.

Цифра: до 40% времени уходит на согласования. Что думаете — автоматизировали бы посты?

EOF

cat > "$JOB_DIR/image_prompt.txt" <<EOF
Extreme close-up of sea salt crystals on deep black background #0a0a0b, single amber accent light #f59e0b, dark editorial food-tech aesthetic, macro detail, no people, no text, square 1:1, raw style

Negative: watermark, text, people, bright background, cartoon

Platform: ${PLATFORM} | Blogger: ${BLOGGER} | Job: ${JOB_ID}
EOF

say "Health: OpenClaw gateway"
if curl -fsS "$GATEWAY_URL/healthz" >/dev/null; then
  echo "OK $GATEWAY_URL/healthz"
else
  echo "FAIL: gateway недоступен ($GATEWAY_URL). Подними: docker compose up -d openclaw-gateway"
  exit 1
fi

if [[ "$SMOKE_ONLY" -eq 1 ]]; then
  echo "Smoke-only: готово (job-создание + health)."
  exit 0
fi

cli() {
  docker compose --profile cli run --rm -T openclaw-cli "$@"
}

if [[ "$RUN_LENS" -eq 1 ]]; then
  say "Lens: text_review"
  cli openclaw agent --agent lens --session-id "$SESSION_KEY" \
    --message "JOB_SCOPE: job_id=$JOB_ID | blogger=$BLOGGER | platform=$PLATFORM | mode=text_review. Прочитай draft и brand-файлы по путям в SOUL. Сохрани final.md при APPROVE. Путь к draft: /home/node/shared/bloggers/$BLOGGER/jobs/$JOB_ID/draft_v1.md" \
    --timeout 300 --json 2>/dev/null | head -c 2000 || true
  echo ""

  say "Lens: prompt_review"
  cli openclaw agent --agent lens --session-id "$SESSION_KEY" \
    --message "JOB_SCOPE: job_id=$JOB_ID | blogger=$BLOGGER | platform=$PLATFORM | mode=prompt_review. Проверь image_prompt.txt по критериям." \
    --timeout 300 --json 2>/dev/null | head -c 2000 || true
  echo ""
fi

if [[ "$RUN_PIXEL" -eq 1 ]]; then
  say "Pixel: генерация (pixel_upload.py)"
  python3 "$ROOT/shared/scripts/pixel_upload.py" \
    --job_id "$JOB_ID" \
    --blogger "$BLOGGER" \
    --platform "$PLATFORM" \
    --prompt_file "$JOB_DIR/image_prompt.txt"
fi

if [[ "$RUN_APPROVAL" -eq 1 ]]; then
  CFG="$ROOT/shared/bloggers/$BLOGGER/channels/$PLATFORM/config.json"
  if [[ ! -f "$CFG" ]]; then
    echo "Нет $CFG — укажи BLOGGER/PLATFORM или создай config.json"
    exit 1
  fi
  APP_JSON="$ROOT/shared/approvals/${JOB_ID}.json"
  python3 - "$CFG" "$JOB_DIR" "$JOB_ID" "$BLOGGER" "$PLATFORM" "$APP_JSON" <<'PY'
import json, sys
cfg_path, job_dir, job_id, blogger, platform, out_path = sys.argv[1:7]
with open(cfg_path, encoding="utf-8") as f:
    channel_id = json.load(f)["channel_id"]
data = {
    "job_id": job_id,
    "blogger": blogger,
    "platform": platform,
    "channel_id": channel_id,
    "content": open(f"{job_dir}/draft_v1.md", encoding="utf-8").read(),
    "image_prompt": open(f"{job_dir}/image_prompt.txt", encoding="utf-8").read(),
    "image_url": "",
}
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("Wrote", out_path)
PY
  say "n8n: POST $N8N_URL/webhook/approval-send"
  RESP=$(curl -sS -X POST "$N8N_URL/webhook/approval-send" \
    -H "Content-Type: application/json" \
    -d @"$APP_JSON") || true
  echo "$RESP"
  if echo "$RESP" | grep -q 'Workflow was started\|message'; then
    echo "OK: проверь Telegram (личка владельца) — должно прийти сообщение с кнопками."
  else
    echo "Предупреждение: ответ не похож на успешный старт workflow. Убедись, что n8n запущен и workflow approval-send активен."
  fi
fi

say "Готово"
echo "Папка задачи: $JOB_DIR"
echo "Повтор с Lens: bash scripts/test-workflow.sh --lens"
echo "Повтор approval: bash scripts/test-workflow.sh --approval"
