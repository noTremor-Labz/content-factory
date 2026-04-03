#!/bin/bash
# Импорт credential «Telegram References bot» и workflow references-style-examples в n8n (Docker).
# Требует: TELEGRAM_REFERENCES_BOT_TOKEN в .env, sqlite3 на хосте, docker compose.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck source=/dev/null
source "$ROOT/scripts/load-env.sh"
load_env "$ROOT"

TOKEN="${TELEGRAM_REFERENCES_BOT_TOKEN:?Задай TELEGRAM_REFERENCES_BOT_TOKEN в .env}"
WF_SRC="$ROOT/n8n/workflows/references-style-examples.json"
CRED_IMPORT="$ROOT/shared/n8n/references-credential-import.json"
CRED_EXPORT="$ROOT/shared/n8n/.tmp-creds-decrypted.json"

if [ ! -f "$WF_SRC" ]; then
  echo "❌ Нет файла $WF_SRC"
  exit 1
fi

command -v sqlite3 >/dev/null || { echo "❌ Нужен sqlite3 (brew install sqlite)"; exit 1; }

mkdir -p "$ROOT/shared/n8n"

python3 << PY
import json
import os
import secrets
import string

def _cred_id():
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(16))

token = os.environ["TELEGRAM_REFERENCES_BOT_TOKEN"]
row = {
    "id": _cred_id(),
    "name": "Telegram References bot",
    "type": "telegramApi",
    "data": {"accessToken": token},
}
with open("$CRED_IMPORT", "w", encoding="utf-8") as f:
    json.dump([row], f, ensure_ascii=False, indent=2)
PY

echo "=== import:credentials ==="
if ! docker compose exec -T n8n n8n import:credentials --input="/home/node/shared/n8n/references-credential-import.json"; then
  echo "⚠️  import:credentials завершился с ошибкой — проверь лог выше."
fi

echo "=== export:credentials (decrypted) — только для чтения id ==="
rm -f "$CRED_EXPORT"
docker compose exec -T n8n n8n export:credentials --all --decrypted --output="/home/node/shared/n8n/.tmp-creds-decrypted.json"

CRED_ID="$(
  CRED_EXPORT="$CRED_EXPORT" python3 -c "
import json, os, sys
path = os.environ.get('CRED_EXPORT', '')
try:
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
except OSError:
    sys.exit(1)
rows = data if isinstance(data, list) else [data]
for r in rows:
    if r.get('name') == 'Telegram References bot' and r.get('type') == 'telegramApi':
        print(r.get('id', '') or '')
        sys.exit(0)
print('')
"
)"

rm -f "$CRED_IMPORT" "$CRED_EXPORT"

if [ -z "${CRED_ID:-}" ]; then
  echo "❌ Не найден credential Telegram References bot после импорта."
  exit 1
fi

echo "✅ Credential id: $CRED_ID"

TMP_WF="$(mktemp)"
python3 << PY
import json
path = r"$WF_SRC"
out = r"$TMP_WF"
cid = r"$CRED_ID"
with open(path, encoding="utf-8") as f:
    wf = json.load(f)
for node in wf.get("nodes", []):
    c = node.get("credentials", {}).get("telegramApi")
    if c and c.get("id") == "REPLACE_WITH_REFERENCES_CREDENTIAL_ID":
        c["id"] = cid
with open(out, "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)
PY

echo "=== import:workflow ==="
WF_DOCKER="/home/node/shared/n8n/references-workflow-import.json"
cp "$TMP_WF" "$ROOT/shared/n8n/references-workflow-import.json"
rm -f "$TMP_WF"
docker compose exec -T n8n n8n import:workflow --input="$WF_DOCKER"
rm -f "$ROOT/shared/n8n/references-workflow-import.json"

echo "=== activate workflow (остановка n8n → sqlite → старт) ==="
docker compose stop n8n
DB_TMP="$(mktemp)"
docker cp n8n:/home/node/.n8n/database.sqlite "$DB_TMP"
sqlite3 "$DB_TMP" "UPDATE workflow_entity SET active = 1 WHERE name = 'references-style-examples';"
docker cp "$DB_TMP" n8n:/home/node/.n8n/database.sqlite
rm -f "$DB_TMP"
docker compose start n8n

echo ""
echo "✅ Готово: credential, workflow references-style-examples, active=1."
echo "   UI: http://127.0.0.1:5678"
