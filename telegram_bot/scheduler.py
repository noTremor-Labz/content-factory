"""APScheduler: cron triggers for OpenClaw + interval stuck-job checks."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from alerter import check_and_alert
import config
from config import (
    BLOGGERS,
    OPENCLAW_HOOKS_TOKEN,
)

logger = logging.getLogger(__name__)


async def call_openclaw_agent(agent_id: str, payload: dict[str, Any]) -> Any:
    """POST {OPENCLAW_API_URL}/hooks/agent — канонический HTTP-вход OpenClaw (не /agents/.../run)."""
    if not OPENCLAW_HOOKS_TOKEN:
        logger.error("OPENCLAW_HOOKS_TOKEN is empty; cannot call /hooks/agent")
        return {"error": "missing OPENCLAW_HOOKS_TOKEN"}
    url = f"{config.OPENCLAW_API_URL}/hooks/agent"
    headers = {
        "Authorization": f"Bearer {OPENCLAW_HOOKS_TOKEN}",
        "Content-Type": "application/json",
    }
    body = {
        "agentId": agent_id,
        "message": json.dumps(payload, ensure_ascii=False),
        "wakeMode": "wake",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=body, headers=headers)
        logger.info(
            "OpenClaw %s → HTTP %d: %s",
            agent_id,
            response.status_code,
            response.text[:200],
        )
        try:
            return response.json()
        except Exception:
            return {"raw": response.text, "status_code": response.status_code}

scheduler = AsyncIOScheduler()
_scheduler_configured = False


async def trigger_daily_queue() -> None:
    for blogger in BLOGGERS:
        try:
            await call_openclaw_agent(
                "director",
                {"task": "daily_content", "blogger": blogger},
            )
        except Exception:
            logger.exception("daily_content failed for %s", blogger)


async def trigger_scout_trends() -> None:
    try:
        await call_openclaw_agent("scout", {"mode": "planning"})
    except Exception:
        logger.exception("scout planning failed")


async def check_stuck_jobs() -> None:
    try:
        await check_and_alert()
    except Exception:
        logger.exception("check_and_alert failed")


def setup_scheduler() -> None:
    global _scheduler_configured
    if _scheduler_configured:
        return
    scheduler.add_job(
        trigger_daily_queue,
        "cron",
        hour=8,
        minute=0,
        id="trigger_daily_queue",
        replace_existing=True,
    )
    scheduler.add_job(
        trigger_scout_trends,
        "cron",
        hour=10,
        minute=0,
        id="trigger_scout_trends",
        replace_existing=True,
    )
    scheduler.add_job(
        check_stuck_jobs,
        "interval",
        minutes=5,
        id="check_stuck_jobs",
        replace_existing=True,
    )
    _scheduler_configured = True


async def start_scheduler() -> None:
    setup_scheduler()
    if not scheduler.running:
        scheduler.start()
    logger.info("APScheduler started (daily 08:00 / 10:00, stuck every 5m)")
