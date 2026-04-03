"""Send post preview to admin chat: caption + optional image + inline buttons."""

from __future__ import annotations

import html
import logging
from pathlib import Path

from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from bot_app import bot
import config
from config import APPROVAL_CAPTION_MAX, TELEGRAM_OWNER_ID

logger = logging.getLogger(__name__)

APPROVAL_SENT_FLAG = "approval_sent.flag"


def get_publish_channel(blogger: str, channel_type: str = "food") -> str | None:
    """Возвращает channel_id для блогера и типа канала. None если канала нет."""
    channels = config.BLOGGERS.get(blogger, {}).get("channels", {})
    return channels.get(channel_type)


def infer_channel_type(job_dir: Path, default: str = "food") -> str:
    """Пытается извлечь channel_type (food/vibe) из файлов job.

    Источник: чаще всего draft_v1.md (строка вида "Канал: tg-food" / "Канал: tg-vibe"),
    но при отсутствии проверяем и другие файлы.
    """
    # Проверяем самые вероятные файлы сначала
    for name in ("draft_v1.md", "ready.md", "content_plan.md", "final.md", "image_prompt.txt"):
        p = job_dir / name
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if "tg-vibe" in text or "tomas-vibe" in text:
            return "vibe"
        if "tg-food" in text or "tomas-food" in text:
            return "food"
    return default


def should_send_approval(job_dir: Path) -> bool:
    """True if ready.md exists and we should notify admin (not yet published / rejected)."""
    ready = job_dir / "ready.md"
    if not ready.is_file():
        return False
    if (job_dir / "published.lock").exists():
        return False
    if (job_dir / "published.flag").exists():
        return False
    if (job_dir / "rejected.flag").exists():
        return False

    sent = job_dir / APPROVAL_SENT_FLAG
    if not sent.exists():
        return True
    return ready.stat().st_mtime > sent.stat().st_mtime


def _caption(blogger: str, job_id: str, body: str) -> str:
    snippet = body[:APPROVAL_CAPTION_MAX]
    if len(body) > APPROVAL_CAPTION_MAX:
        snippet += "…"
    safe = html.escape(snippet)
    header = (
        f"📋 <b>{html.escape(blogger)}</b> | job: <code>{html.escape(job_id)}</code>\n\n"
        f"{safe}"
    )
    return header


def _keyboard(blogger: str, job_id: str, channel_type: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Опубликовать",
                    callback_data=f"approve:{blogger}:{job_id}:{channel_type}",
                ),
                InlineKeyboardButton(
                    text="✏️ Правки",
                    callback_data=f"revise:{blogger}:{job_id}:{channel_type}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject:{blogger}:{job_id}:{channel_type}",
                ),
            ],
        ]
    )


async def send_for_approval(blogger: str, job_id: str, job_dir: Path) -> None:
    ready_path = job_dir / "ready.md"
    text = ready_path.read_text(encoding="utf-8", errors="replace")

    channel_type = infer_channel_type(job_dir)
    _ = get_publish_channel(blogger, channel_type)  # вычисляем, чтобы не ломать расширение логов

    image_path = job_dir / "image.jpg"
    caption = _caption(blogger, job_id, text)
    kb = _keyboard(blogger, job_id, channel_type)
    chat_id = TELEGRAM_OWNER_ID

    if image_path.is_file():
        await bot.send_photo(
            chat_id=chat_id,
            photo=FSInputFile(image_path),
            caption=caption,
            parse_mode="HTML",
            reply_markup=kb,
        )
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=caption,
            parse_mode="HTML",
            reply_markup=kb,
        )

    (job_dir / APPROVAL_SENT_FLAG).touch()
    logger.info("Approval sent for %s / %s", blogger, job_id)
