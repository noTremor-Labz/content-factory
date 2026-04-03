"""Inline keyboard callback router: approve / revise / reject."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import CallbackQuery

from approval import APPROVAL_SENT_FLAG
from scheduler import call_openclaw_agent
from paths_util import get_job_dir

logger = logging.getLogger(__name__)

router = Router(name="callbacks")


@router.callback_query()
async def handle_callback(callback: CallbackQuery) -> None:
    if not callback.data or not callback.message:
        await callback.answer("Нет данных", show_alert=True)
        return

    try:
        action, blogger, job_id = callback.data.split(":", 2)
    except ValueError:
        await callback.answer("Некорректные данные", show_alert=True)
        return
    job_dir = get_job_dir(blogger, job_id)

    if action == "approve":
        lock = job_dir / "published.lock"
        flag = job_dir / "published.flag"
        rej = job_dir / "rejected.flag"
        if lock.exists() or flag.exists() or rej.exists():
            await callback.answer("Уже обработано", show_alert=True)
            return
        lock.touch()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer("✅ Отправлено на публикацию")
        await callback.message.reply(
            f"✅ Апрувнуто: {blogger} / {job_id}",
        )
        logger.info("Approved %s / %s", blogger, job_id)

    elif action == "revise":
        af = job_dir / APPROVAL_SENT_FLAG
        if af.exists():
            af.unlink(missing_ok=True)
        await call_openclaw_agent(
            "director",
            {"task": "revise", "blogger": blogger, "job_id": job_id},
        )
        await callback.answer("✏️ Отправлено на правки")
        await callback.message.reply(f"✏️ На правках: {blogger} / {job_id}")
        logger.info("Revise requested %s / %s", blogger, job_id)

    elif action == "reject":
        (job_dir / "rejected.flag").touch()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer("❌ Отклонено")
        await callback.message.reply(f"❌ Отклонено: {blogger} / {job_id}")
        logger.info("Rejected %s / %s", blogger, job_id)

    else:
        await callback.answer("Неизвестное действие", show_alert=True)
