import os
import sys
import shutil
import tempfile
import time
from pathlib import Path

os.environ.update(
    {
        "TELEGRAM_APPROVAL_BOT_TOKEN": "123456:TEST",
        "TELEGRAM_OWNER_ID": "-100123456",
        "OPENCLAW_API_URL": "http://localhost:8080",
        "SHARED_BASE_PATH": "/tmp/test_shared/bloggers",
        "TELEGRAM_CHANNEL_TOMAS_FOOD": "-100111",
        "TELEGRAM_CHANNEL_TOMAS_VIBE": "-100112",
        "STUCK_THRESHOLD_HOURS": "0.0001",  # ~0.36 секунды для теста
    },
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alerter import is_job_stuck  # noqa: E402

base = Path(tempfile.mkdtemp())
job_dir = base / "tomas" / "jobs" / "test-stuck"
job_dir.mkdir(parents=True)

try:
    # Тест 1: нет файлов → не завис
    assert is_job_stuck(job_dir) is False, "Пустой job не должен считаться зависшим"

    # Тест 2: есть draft, нет approved, старый → завис
    (job_dir / "draft_v1.md").write_text("черновик", encoding="utf-8")
    time.sleep(0.5)  # ждём дольше порога
    assert is_job_stuck(job_dir) is True, (
        "Старый draft без approved должен быть stuck"
    )

    # Тест 3: есть approved → не завис
    (job_dir / "draft_approved.md").write_text("апрувнуто", encoding="utf-8")
    assert is_job_stuck(job_dir) is False, (
        "С approved не должен быть stuck"
    )
    (job_dir / "draft_approved.md").unlink()

    # Тест 4: есть published.lock → не завис
    (job_dir / "published.lock").touch()
    assert is_job_stuck(job_dir) is False, "С published.lock не должен быть stuck"
    (job_dir / "published.lock").unlink()

    # Тест 5: есть rejected.flag → не завис
    (job_dir / "rejected.flag").touch()
    assert is_job_stuck(job_dir) is False, "С rejected.flag не должен быть stuck"
finally:
    shutil.rmtree(base, ignore_errors=True)

print("✅ alerter stuck detection OK")

