#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
bash "$ROOT/scripts/0-install-deps.sh"
bash "$ROOT/scripts/1-openclaw-setup.sh"
bash "$ROOT/scripts/2-create-agents.sh"
bash "$ROOT/scripts/3-configure.sh"
echo ""
echo "=== Полная установка завершена ==="
echo "Проверка: bash scripts/validate.sh"
