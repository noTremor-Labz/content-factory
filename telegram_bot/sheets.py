"""Google Sheets append via gspread + service account (no OAuth)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

import gspread

from config import BLOGGERS, GOOGLE_SA_JSON_PATH, SHEETS_SPREADSHEET_NAME

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
        channel = BLOGGERS.get(blogger, {}).get("channel", "")
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
