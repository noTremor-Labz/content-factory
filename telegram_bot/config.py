"""Environment-driven configuration for the Telegram automation bot."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
# Primary: TELEGRAM_ADMIN_CHAT_ID; fallbacks align with content-factory / n8n naming
_raw_admin = (
    os.environ.get("TELEGRAM_ADMIN_CHAT_ID")
    or os.environ.get("APPROVE_CHAT_ID")
    or os.environ.get("TELEGRAM_APPROVAL_CHAT_ID")
    or ""
)
TELEGRAM_ADMIN_CHAT_ID = _raw_admin.strip()

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

TELEGRAM_CHANNEL_TOMAS = os.environ.get("TELEGRAM_CHANNEL_TOMAS", "").strip()
TELEGRAM_CHANNEL_MISHA = os.environ.get("TELEGRAM_CHANNEL_MISHA", "").strip()
TELEGRAM_CHANNEL_YULYA = os.environ.get("TELEGRAM_CHANNEL_YULYA", "").strip()
TELEGRAM_CHANNEL_NASIK = os.environ.get("TELEGRAM_CHANNEL_NASIK", "").strip()

BLOGGERS: dict[str, dict[str, str]] = {
    "tomas": {"channel": TELEGRAM_CHANNEL_TOMAS},
    "misha": {"channel": TELEGRAM_CHANNEL_MISHA},
    "yulya": {"channel": TELEGRAM_CHANNEL_YULYA},
    "nasik": {"channel": TELEGRAM_CHANNEL_NASIK},
}

GOOGLE_SA_JSON_PATH = os.environ.get("GOOGLE_SA_JSON_PATH", "").strip()
SHEETS_SPREADSHEET_NAME = os.environ.get("SHEETS_SPREADSHEET_NAME", "").strip()

STUCK_THRESHOLD_HOURS = float(os.environ.get("STUCK_THRESHOLD_HOURS", "2"))

HTTP_TIMEOUT_SECONDS = float(os.environ.get("HTTP_TIMEOUT_SECONDS", "30"))

APPROVAL_CAPTION_MAX = int(os.environ.get("APPROVAL_CAPTION_MAX", "1000"))
