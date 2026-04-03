"""Single shared Bot instance (avoids circular imports with main)."""

from __future__ import annotations

from aiogram import Bot

from config import TELEGRAM_APPROVAL_BOT_TOKEN

bot = Bot(token=TELEGRAM_APPROVAL_BOT_TOKEN)
