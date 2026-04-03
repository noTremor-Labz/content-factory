"""Google Sheets append via gspread + service account (no OAuth)."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

import gspread

from config import BLOGGERS, GOOGLE_SA_JSON_PATH, SHARED_BASE_PATH, SHEETS_SPREADSHEET_NAME

logger = logging.getLogger(__name__)

_gc: Any = None


def _client() -> Any:
    global _gc
    if _gc is None:
        if not GOOGLE_SA_JSON_PATH:
            raise RuntimeError("GOOGLE_SA_JSON_PATH is not set")
        _gc = gspread.service_account(filename=GOOGLE_SA_JSON_PATH)
    return _gc


async def log_published(blogger: str, job_id: str) -> None:
    def _sync_append() -> None:
        gc = _client()
        sh = gc.open(SHEETS_SPREADSHEET_NAME)
        ws = sh.worksheet("published_log")
        channel = ""
        channel_type = "food"
        lock_path = SHARED_BASE_PATH / blogger / "jobs" / job_id / "published.lock"
        if lock_path.is_file():
            try:
                data = json.loads(lock_path.read_text(encoding="utf-8", errors="replace"))
                channel_type = data.get("channel_type") or data.get("publish_channel_type") or channel_type
                channel = data.get("channel_id") or ""
            except Exception:
                # Если published.lock не JSON — просто логируем канал по env.
                pass

        if not channel:
            channel = BLOGGERS.get(blogger, {}).get("channels", {}).get(channel_type, "") or ""
        ws.append_row(
            [
                datetime.now().isoformat(),
                blogger,
                job_id,
                channel,
            ]
        )

    await asyncio.to_thread(_sync_append)
    logger.info("Sheets: logged published %s / %s", blogger, job_id)
