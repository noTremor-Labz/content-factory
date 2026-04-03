#!/usr/bin/env bash
# Проверка approval-send (3 ветки) и опционально telegram-router (approve_a → published.lock).
# Запуск из корня репозитория: bash scripts/verify-approval-media.sh
# Требуется: n8n на $N8N_URL, активные workflow approval-send и telegram-router.
#
# После git pull импортируй workflow в контейнер n8n (иначе в БД старая версия):
#   docker cp n8n-export-approval-send.json n8n:/tmp/a.json
#   docker cp n8n-export-telegram-router.json n8n:/tmp/t.json
#   docker exec n8n n8n import:workflow --input=/tmp/a.json
#   docker exec n8n n8n import:workflow --input=/tmp/t.json
#   docker exec n8n n8n publish:workflow --id=4lq3sy9j6qlzH99W
#   docker exec n8n n8n publish:workflow --id=TwB0v8AOQ8CQmJCg
#   docker restart n8n
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck source=/dev/null
source "$ROOT/scripts/load-env.sh"
load_env "$ROOT"

N8N_URL="${N8N_URL:-http://127.0.0.1:5678}"
N8N_USER="${N8N_BASIC_AUTH_USER:-admin}"
N8N_PASS="${N8N_BASIC_AUTH_PASSWORD:-localdev123}"
BLOGGER="${BLOGGER:-tomas-food}"
PLATFORM="${PLATFORM:-tg}"

CFG="$ROOT/shared/bloggers/$BLOGGER/channels/$PLATFORM/config.json"
if [[ ! -f "$CFG" ]]; then
  echo "Нет $CFG — задай BLOGGER/PLATFORM"
  exit 1
fi

CHANNEL_ID=$(python3 -c "import json; print(json.load(open('$CFG'))['channel_id'])")

say() { printf '\n=== %s ===\n' "$*"; }

say "Health n8n"
curl -fsS "$N8N_URL/healthz" >/dev/null

AUTH=(-u "$N8N_USER:$N8N_PASS")
JOB_BASE="verify-as-$(date +%Y%m%d-%H%M%S)"
BASE_OBJ=$(python3 -c "import json; print(json.dumps({
  'job_id': '$JOB_BASE',
  'blogger': '$BLOGGER',
  'platform': '$PLATFORM',
  'channel_id': '$CHANNEL_ID',
  'content': 'Автотест approval-send',
}))")

post_approval() {
  local name="$1"
  local payload="$2"
  say "$name"
  local resp
  resp=$(curl -sS "${AUTH[@]}" -X POST "$N8N_URL/webhook/approval-send" \
    -H "Content-Type: application/json" \
    -d "$payload") || true
  echo "$resp"
  echo "$resp" | grep -q 'Workflow was started' || {
    echo "FAIL: ожидался {\"message\":\"Workflow was started\"}"
    exit 1
  }
}

TWO=$(python3 -c "import json,sys; b=json.loads(sys.argv[1]); b['media_url']='https://via.placeholder.com/150'; b['media_url_b']='https://via.placeholder.com/151'; print(json.dumps(b))" "$BASE_OBJ")
ONE=$(python3 -c "import json,sys; b=json.loads(sys.argv[1]); b['media_url']='https://via.placeholder.com/150'; print(json.dumps(b))" "$BASE_OBJ")
NONE=$(python3 -c "import json,sys; b=json.loads(sys.argv[1]); print(json.dumps(b))" "$BASE_OBJ")

post_approval "(a) два URL (альбом + 4 кнопки: A / B / Правки / Отклонить)" "$TWO"
post_approval "(b) один URL (фото + 3 кнопки)" "$ONE"
post_approval "(c) без media_url (текст + предупреждение + 3 кнопки)" "$NONE"

if [[ "${VERIFY_ROUTER:-}" == "1" ]]; then
  say "telegram-router: approve_a → published.lock"
  JOB_R="verify-r-$(date +%Y%m%d-%H%M%S)"
  JOB_DIR="$ROOT/shared/bloggers/$BLOGGER/jobs/$JOB_R"
  mkdir -p "$JOB_DIR"
  APP_JSON="$ROOT/shared/approvals/${JOB_R}.json"
  python3 - "$APP_JSON" "$JOB_R" "$BLOGGER" "$PLATFORM" "$CHANNEL_ID" <<'PY'
import json, sys
path, job, blogger, platform, channel_id = sys.argv[1:6]
data = {
  "job_id": job,
  "blogger": blogger,
  "platform": platform,
  "channel_id": channel_id,
  "content": "Тест router approve_a",
  "image_prompt": "x",
  "media_url": "https://via.placeholder.com/100",
  "media_url_b": "https://via.placeholder.com/101",
}
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(path)
PY
  CB="approve_a_${JOB_R}"
  curl -sS "${AUTH[@]}" -X POST "$N8N_URL/webhook/telegram-router" \
    -H "Content-Type: application/json" \
    -d "{\"callback_query\":{\"id\":\"cb-v\",\"from\":{\"id\":492912584},\"message\":{\"message_id\":1,\"chat\":{\"id\":492912584}},\"data\":\"${CB}\"}}" >/dev/null
  sleep 2
  LOCK="$JOB_DIR/published.lock"
  if [[ ! -f "$LOCK" ]]; then
    echo "FAIL: нет $LOCK после approve_a"
    exit 1
  fi
  python3 -c "import json; d=json.load(open('$LOCK')); assert d.get('selected_media_url','').startswith('http')"
  echo "OK $(cat "$LOCK")"
fi

say "Парсинг callback_data (Node)"
node <<'NODE'
function parse(cbData) {
  let action, jobId;
  if (cbData.startsWith('approve_a_')) {
    action = 'approve_a';
    jobId = cbData.slice('approve_a_'.length);
  } else if (cbData.startsWith('approve_b_')) {
    action = 'approve_b';
    jobId = cbData.slice('approve_b_'.length);
  } else if (cbData.startsWith('approve_')) {
    action = 'approve';
    jobId = cbData.slice('approve_'.length);
  } else if (cbData.startsWith('reject_')) {
    action = 'reject';
    jobId = cbData.slice('reject_'.length);
  } else {
    throw new Error('bad ' + cbData);
  }
  return { action, jobId };
}
const t = [
  ['approve_20260402-001', 'approve', '20260402-001'],
  ['approve_a_20260402-001', 'approve_a', '20260402-001'],
  ['approve_b_20260402-001', 'approve_b', '20260402-001'],
  ['reject_abc', 'reject', 'abc'],
];
for (const [s, expA, expJ] of t) {
  const p = parse(s);
  if (p.action !== expA || p.jobId !== expJ) {
    console.error('FAIL', s, p);
    process.exit(1);
  }
}
console.log('OK parse tests');
NODE

say "Готово: approval-send OK; парсинг OK"
if [[ "${VERIFY_ROUTER:-}" != "1" ]]; then
  echo "Подсказка: полный тест router — VERIFY_ROUTER=1 bash scripts/verify-approval-media.sh"
fi
