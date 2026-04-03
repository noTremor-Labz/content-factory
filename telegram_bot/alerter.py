"""Periodic scan for stuck jobs → Telegram alerts (deduplicated per job)."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from bot_app import bot
from config import SHARED_BASE_PATH, STUCK_THRESHOLD_HOURS, TELEGRAM_OWNER_ID
from paths_util import extract_blogger_from_job_dir

logger = logging.getLogger(__name__)

STUCK_ALERT_FLAG = "stuck_alert_sent.flag"


def is_job_stuck(job_dir: Path) -> bool:
    """True if job looks stuck on draft review (time threshold based)."""
    if not job_dir.is_dir():
        return False

    has_draft = (job_dir / "draft_v1.md").exists()
    has_approved = (job_dir / "draft_approved.md").exists()
    has_lock = (job_dir / "published.lock").exists()
    has_flag = (job_dir / "published.flag").exists()
    has_rejected = (job_dir / "rejected.flag").exists()

    if has_rejected or has_flag or has_lock:
        return False
    if not has_draft:
        return False
    if has_approved:
        return False

    draft_path = job_dir / "draft_v1.md"
    mtime = draft_path.stat().st_mtime
    age_hours = (time.time() - mtime) / 3600.0
    return age_hours > STUCK_THRESHOLD_HOURS


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

        if has_draft and not has_approved and is_job_stuck(job_dir):
            if alert_path.exists():
                continue

            draft_path = job_dir / "draft_v1.md"
            age_hours = (now - draft_path.stat().st_mtime) / 3600.0
            blogger = extract_blogger_from_job_dir(job_dir)
            job_id = job_dir.name
            text = (
                f"⚠️ Завис на ревью: {blogger} / {job_id}\n"
                f"Ждёт {age_hours:.1f}ч"
            )
            try:
                await bot.send_message(
                    TELEGRAM_OWNER_ID,
                    text,
                )
                alert_path.touch()
                logger.info("Stuck alert sent for %s / %s", blogger, job_id)
            except Exception:
                logger.exception("Failed to send stuck alert for %s", job_dir)
            continue

        if alert_path.exists():
            alert_path.unlink(missing_ok=True)
