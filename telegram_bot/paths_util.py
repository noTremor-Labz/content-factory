"""Path helpers for shared/bloggers/{blogger}/jobs/{job_id}/ layout."""

from __future__ import annotations

from pathlib import Path

from config import SHARED_BASE_PATH


def get_job_dir(blogger: str, job_id: str) -> Path:
    return SHARED_BASE_PATH / blogger / "jobs" / job_id


def extract_blogger_and_job_from_ready(ready_path: Path) -> tuple[str, str]:
    job_dir = ready_path.parent
    job_id = job_dir.name
    blogger = job_dir.parent.parent.name
    return blogger, job_id


def extract_blogger_from_job_dir(job_dir: Path) -> str:
    return job_dir.parent.parent.name


def extract_blogger(path: Path) -> str:
    """Extract blogger name from a ready-like file path."""
    job_dir = path.parent
    return job_dir.parent.parent.name


def extract_job_id(path: Path) -> str:
    """Extract job_id from a ready-like file path."""
    job_dir = path.parent
    return job_dir.name
