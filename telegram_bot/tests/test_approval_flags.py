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
    },
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from approval import should_send_approval  # noqa: E402

base = Path(tempfile.mkdtemp())
try:
    job_dir = base / "tomas" / "jobs" / "test-001"
    job_dir.mkdir(parents=True)
    (job_dir / "ready.md").write_text("Тестовый пост", encoding="utf-8")

    # --- Тест 1: нет флагов → должен отправить ---
    assert should_send_approval(job_dir) is True, "Без флагов должен вернуть True"

    # --- Тест 2: есть published.lock → не отправлять ---
    (job_dir / "published.lock").touch()
    assert should_send_approval(job_dir) is False, (
        "При published.lock должен вернуть False"
    )
    (job_dir / "published.lock").unlink()

    # --- Тест 3: есть published.flag → не отправлять ---
    (job_dir / "published.flag").touch()
    assert should_send_approval(job_dir) is False, (
        "При published.flag должен вернуть False"
    )
    (job_dir / "published.flag").unlink()

    # --- Тест 4: есть rejected.flag → не отправлять ---
    (job_dir / "rejected.flag").touch()
    assert should_send_approval(job_dir) is False, (
        "При rejected.flag должен вернуть False"
    )
    (job_dir / "rejected.flag").unlink()

    # --- Тест 5: approval_sent.flag старее ready.md → не отправлять ---
    flag = job_dir / "approval_sent.flag"
    flag.touch()
    time.sleep(0.01)
    # ready.md НЕ обновляем — флаг новее
    assert should_send_approval(job_dir) is False, (
        "Если флаг новее ready.md — не отправлять"
    )

    # --- Тест 6: ready.md обновлён после флага → отправить снова ---
    time.sleep(0.01)
    (job_dir / "ready.md").write_text("Обновлённый пост", encoding="utf-8")
    assert should_send_approval(job_dir) is True, (
        "Если ready.md новее флага — отправить снова"
    )
finally:
    shutil.rmtree(base, ignore_errors=True)

print("✅ approval flags logic OK")

