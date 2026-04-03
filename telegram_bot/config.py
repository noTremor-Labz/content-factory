"""Environment-driven configuration for the Telegram automation bot."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# telegram_bot/ is the approval bot (previews + approve/revise/reject buttons)
TELEGRAM_APPROVAL_BOT_TOKEN = os.environ.get("TELEGRAM_APPROVAL_BOT_TOKEN", "").strip()
TELEGRAM_OWNER_ID = os.environ.get("TELEGRAM_OWNER_ID", "").strip()

OPENCLAW_API_URL = (
    os.environ.get("OPENCLAW_API_URL")
    or os.environ.get("OPENCLAW_GATEWAY_INTERNAL_URL")
    or ""
).rstrip("/")

SHARED_BASE_PATH = Path(
    os.environ.get("SHARED_BASE_PATH", os.environ.get("HOST_SHARED_PATH", "./shared"))
).expanduser()
# Normalize to .../bloggers if env points at repo `shared/`
if SHARED_BASE_PATH.name != "bloggers":
    candidate = SHARED_BASE_PATH / "bloggers"
    if candidate.is_dir():
        SHARED_BASE_PATH = candidate

TELEGRAM_CHANNEL_TOMAS_FOOD = os.environ.get("TELEGRAM_CHANNEL_TOMAS_FOOD", "").strip()
TELEGRAM_CHANNEL_TOMAS_VIBE = os.environ.get("TELEGRAM_CHANNEL_TOMAS_VIBE", "").strip()

# Note: only `tomas` has 2 Telegram channels; other bloggers have none.
BLOGGERS: dict[str, dict[str, dict[str, str]]] = {
    "tomas": {
        "channels": {
            "food": TELEGRAM_CHANNEL_TOMAS_FOOD,
            "vibe": TELEGRAM_CHANNEL_TOMAS_VIBE,
        }
    },
    "misha": {"channels": {}},
    "yulya": {"channels": {}},
    "nasik": {"channels": {}},
}

GOOGLE_SA_JSON_PATH = os.environ.get("GOOGLE_SA_JSON_PATH", "").strip()
SHEETS_SPREADSHEET_NAME = os.environ.get("SHEETS_SPREADSHEET_NAME", "").strip()

STUCK_THRESHOLD_HOURS = float(os.environ.get("STUCK_THRESHOLD_HOURS", "2"))

HTTP_TIMEOUT_SECONDS = float(os.environ.get("HTTP_TIMEOUT_SECONDS", "30"))

APPROVAL_CAPTION_MAX = int(os.environ.get("APPROVAL_CAPTION_MAX", "1000"))
