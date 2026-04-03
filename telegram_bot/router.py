"""Inline keyboard callback router: approve / revise / reject."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from aiogram import Router
from aiogram.types import CallbackQuery

from approval import APPROVAL_SENT_FLAG
import config
from scheduler import call_openclaw_agent
from paths_util import get_job_dir

logger = logging.getLogger(__name__)

router = Router(name="callbacks")


def get_publish_channel(blogger: str, channel_type: str = "food") -> str | None:
    """Возвращает channel_id для блогера и типа канала. None если канала нет."""
    channels = config.BLOGGERS.get(blogger, {}).get("channels", {})
    return channels.get(channel_type)


def parse_callback_data(data: str) -> tuple[str, str, str, str]:
    """Parse callback_data into (action, blogger, job_id, channel_type)."""
    parts = data.split(":")
    if len(parts) == 3:
        action, blogger, job_id = parts
        channel_type = "food"
    elif len(parts) == 4:
        action, blogger, job_id, channel_type = parts
    else:
        raise ValueError(f"Invalid callback_data: {data}")
    return action, blogger, job_id, channel_type


@router.callback_query()
async def handle_callback(callback: CallbackQuery) -> None:
    if not callback.data or not callback.message:
        await callback.answer("Нет данных", show_alert=True)
        return

    try:
        action, blogger, job_id, channel_type = parse_callback_data(callback.data)
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
        # Все артефакты ниже — синхронно, до любых await (launch читает их с диска).
        now_iso = datetime.now(timezone.utc).isoformat()
        channel_id = get_publish_channel(blogger, channel_type)

        # 1. published.lock
        lock_payload = {
            "decision": "approve",
            "approved_at": now_iso,
            "channel_type": channel_type,
            "channel_id": channel_id,
        }
        lock.write_text(json.dumps(lock_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        # 2. config.json
        config_payload = {
            "blogger": blogger,
            "channel_type": channel_type,
            "channel_id": channel_id,
            "platform": "telegram",
            "bot_token_env": "TELEGRAM_DIRECTOR_BOT_TOKEN",
        }
        (job_dir / "config.json").write_text(
            json.dumps(config_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Created config.json for %s / %s", blogger, job_id)

        # 3. job-state.json
        job_state = {
            "decision": "approve",
            "status": "approved",
            "approved_at": now_iso,
            "blogger": blogger,
            "job_id": job_id,
        }
        (job_dir / "job-state.json").write_text(
            json.dumps(job_state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 4. final.md — копия из черновика, если ещё нет
        final_path = job_dir / "final.md"
        if not final_path.exists():
            for src_name in ("draft_final.md", "draft_approved.md", "draft_v1.md"):
                src_path = job_dir / src_name
                if src_path.exists():
                    final_path.write_text(src_path.read_text(encoding="utf-8"), encoding="utf-8")
                    logger.info("Wrote final.md from %s for %s / %s", src_name, blogger, job_id)
                    break

        # Удаляем сообщение с кнопками
        try:
            await callback.message.delete()
        except Exception:
            await callback.message.edit_reply_markup(reply_markup=None)

        # Удаляем исходное approval-сообщение, если есть meta
        meta_path = job_dir / "approval_meta.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                from bot_app import bot as _bot

                await _bot.delete_message(
                    chat_id=meta["chat_id"],
                    message_id=meta["message_id"],
                )
            except Exception as e:
                logger.warning("Could not delete approval message: %s", e)

        await callback.answer("✅ Отправлено на публикацию")
        await callback.message.answer(
            f"✅ Апрувнуто: {blogger} / {job_id} (канал: {channel_type})",
        )
        logger.info("Approved %s / %s", blogger, job_id)

        # Вызвать launch-агента
        try:
            await call_openclaw_agent(
                "launch",
                {
                    "task": "publish",
                    "blogger": blogger,
                    "job_id": job_id,
                },
            )
            logger.info("Launch agent called for %s / %s", blogger, job_id)
        except Exception as e:
            logger.error("Failed to call launch agent: %s", e)

    elif action == "revise":
        af = job_dir / APPROVAL_SENT_FLAG
        if af.exists():
            af.unlink(missing_ok=True)
        await call_openclaw_agent(
            "director",
            {
                "task": "revise",
                "blogger": blogger,
                "job_id": job_id,
                "channel_type": channel_type,
                "channel_id": get_publish_channel(blogger, channel_type),
            },
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
