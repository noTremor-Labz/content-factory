# shellcheck shell=bash
# Подключается из других скриптов: source "$(dirname "$0")/load-env.sh" && load_env "$ROOT"
load_env() {
  local root="$1"
  set -a
  [ -f "$root/.env" ] && . "$root/.env"
  [ -f "$root/.env.local" ] && . "$root/.env.local"
  [ -f "${HOME}/.config/content-factory.env" ] && . "${HOME}/.config/content-factory.env"
  set +a
}
