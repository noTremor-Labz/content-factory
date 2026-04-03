"""Periodic scan for stuck jobs → Telegram alerts (deduplicated per job)."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from bot_app import bot
from config import SHARED_BASE_PATH, STUCK_THRESHOLD_HOURS, TELEGRAM_ADMIN_CHAT_ID
from paths_util import extract_blogger_from_job_dir

logger = logging.getLogger(__name__)

STUCK_ALERT_FLAG = "stuck_alert_sent.flag"


async def check_and_alert() -> None:
    now = time.time()
    base = SHARED_BASE_PATH
    if not base.is_dir():
        return

    for job_dir in base.glob("*/jobs/*/"):
        if not job_dir.is_dir():
            continue

        has_draft = (job_dir / "draft_v1.md").exists()
        has_approved = (job_dir / "draft_approved.md").exists()
        has_lock = (job_dir / "published.lock").exists()
        has_flag = (job_dir / "published.flag").exists()
        has_rejected = (job_dir / "rejected.flag").exists()

        alert_path = job_dir / STUCK_ALERT_FLAG

        if has_rejected or has_flag or has_lock:
            if alert_path.exists():
                alert_path.unlink(missing_ok=True)
            continue

        if has_draft and not has_approved:
            draft_path = job_dir / "draft_v1.md"
            mtime = draft_path.stat().st_mtime
            age_hours = (now - mtime) / 3600.0
            if age_hours <= STUCK_THRESHOLD_HOURS:
                if alert_path.exists():
                    alert_path.unlink(missing_ok=True)
                continue

            if alert_path.exists():
                continue

            blogger = extract_blogger_from_job_dir(job_dir)
            job_id = job_dir.name
            text = (
                f"⚠️ Завис на ревью: {blogger} / {job_id}\n"
                f"Ждёт {age_hours:.1f}ч"
            )
            try:
                await bot.send_message(
                    TELEGRAM_ADMIN_CHAT_ID,
                    text,
                )
                alert_path.touch()
                logger.info("Stuck alert sent for %s / %s", blogger, job_id)
            except Exception:
                logger.exception("Failed to send stuck alert for %s", job_dir)
            continue

        if alert_path.exists():
            alert_path.unlink(missing_ok=True)
