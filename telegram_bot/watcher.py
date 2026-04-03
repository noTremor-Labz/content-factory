"""Filesystem watcher: new/updated ready.md → approval flow."""

from __future__ import annotations

import logging
from pathlib import Path

from watchfiles import awatch

from approval import send_for_approval, should_send_approval
from config import SHARED_BASE_PATH
from paths_util import extract_blogger_and_job_from_ready

logger = logging.getLogger(__name__)


async def watch_filesystem() -> None:
    base = SHARED_BASE_PATH
    base.mkdir(parents=True, exist_ok=True)
    logger.info("Watching ready.md under %s", base)

    async for changes in awatch(base, recursive=True):
        for _change, path_str in changes:
            p = Path(path_str)
            if p.name != "ready.md":
                continue
            job_dir = p.parent
            if not should_send_approval(job_dir):
                continue
            try:
                blogger, job_id = extract_blogger_and_job_from_ready(p)
            except Exception:
                logger.exception("Bad path for ready.md: %s", p)
                continue
            try:
                await send_for_approval(blogger, job_id, job_dir)
            except Exception:
                logger.exception("send_for_approval failed for %s", job_dir)
