"""Entry point: polling + filesystem watchers + scheduler."""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Dispatcher

from bot_app import bot
from config import (
    OPENCLAW_API_URL,
    SHARED_BASE_PATH,
    TELEGRAM_ADMIN_CHAT_ID,
    TELEGRAM_BOT_TOKEN,
)
from publisher import watch_published
from router import router
from scheduler import start_scheduler
from watcher import watch_filesystem

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def _validate_startup() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is required")
    if not TELEGRAM_ADMIN_CHAT_ID:
        raise SystemExit(
            "TELEGRAM_ADMIN_CHAT_ID (or APPROVE_CHAT_ID / TELEGRAM_APPROVAL_CHAT_ID) is required",
        )
    if not OPENCLAW_API_URL:
        logger.warning(
            "OPENCLAW_API_URL / OPENCLAW_GATEWAY_INTERNAL_URL is empty — "
            "scheduler and revise callbacks will fail until set",
        )
    SHARED_BASE_PATH.mkdir(parents=True, exist_ok=True)
    logger.info("SHARED_BASE_PATH=%s", SHARED_BASE_PATH.resolve())


async def main() -> None:
    _validate_startup()
    dp = Dispatcher()
    dp.include_router(router)

    await asyncio.gather(
        dp.start_polling(bot),
        start_scheduler(),
        watch_filesystem(),
        watch_published(),
    )


if __name__ == "__main__":
    asyncio.run(main())
