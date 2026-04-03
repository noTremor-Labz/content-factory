"""Watch published.flag → Sheets log + admin notification."""

from __future__ import annotations

import logging
from pathlib import Path

from watchfiles import awatch

from bot_app import bot
from config import (
    GOOGLE_SA_JSON_PATH,
    SHARED_BASE_PATH,
    SHEETS_SPREADSHEET_NAME,
    TELEGRAM_ADMIN_CHAT_ID,
)
from paths_util import extract_blogger_from_job_dir
from sheets import log_published

logger = logging.getLogger(__name__)

SHEETS_LOGGED_FLAG = "sheets_logged.flag"


async def notify_published(blogger: str, job_id: str) -> None:
    await bot.send_message(
        TELEGRAM_ADMIN_CHAT_ID,
        f"📢 Опубликовано в канале: {blogger} / {job_id}",
    )


async def _handle_published_flag(path: Path) -> None:
    job_dir = path.parent
    done = job_dir / SHEETS_LOGGED_FLAG
    if done.exists():
        return
    p = job_dir / "published.flag"
    if not p.exists():
        return
    blogger = extract_blogger_from_job_dir(job_dir)
    job_id = job_dir.name

    if SHEETS_SPREADSHEET_NAME and GOOGLE_SA_JSON_PATH:
        try:
            await log_published(blogger, job_id)
        except Exception:
            logger.exception("log_published failed for %s", job_dir)
    else:
        logger.info(
            "Sheets logging skipped (set SHEETS_SPREADSHEET_NAME and GOOGLE_SA_JSON_PATH)",
        )

    try:
        await notify_published(blogger, job_id)
    except Exception:
        logger.exception("notify_published failed for %s", job_dir)

    done.touch()


async def watch_published() -> None:
    base = SHARED_BASE_PATH
    base.mkdir(parents=True, exist_ok=True)
    logger.info("Watching published.flag under %s", base)

    async for changes in awatch(base, recursive=True):
        for _change, path_str in changes:
            p = Path(path_str)
            if p.name != "published.flag":
                continue
            try:
                await _handle_published_flag(p)
            except Exception:
                logger.exception("handle published.flag failed for %s", p)
