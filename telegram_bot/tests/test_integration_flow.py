"""
Симулирует полный flow: появился ready.md → должен создаться approval_sent.flag.
Без реального Telegram — мокаем вызов бота.
"""

import asyncio
import os
import sys
import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ.update(
    {
        "TELEGRAM_APPROVAL_BOT_TOKEN": "123456:TEST",
        "TELEGRAM_OWNER_ID": "-100123456",
        "OPENCLAW_API_URL": "http://localhost:8080",
        "SHARED_BASE_PATH": "",  # переопределим ниже
        "TELEGRAM_CHANNEL_TOMAS_FOOD": "-100111",
        "TELEGRAM_CHANNEL_TOMAS_VIBE": "-100112",
    },
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

base = Path(tempfile.mkdtemp())
job_dir = base / "tomas" / "jobs" / "integ-001"
job_dir.mkdir(parents=True)
(job_dir / "ready.md").write_text("Интеграционный тест", encoding="utf-8")


async def run_test() -> None:
    # Мокаем отправку в Telegram
    with patch("approval.bot") as mock_bot:
        mock_bot.send_message = AsyncMock(return_value=None)
        mock_bot.send_photo = AsyncMock(return_value=None)

        import approval
        import config

        config.SHARED_BASE_PATH = str(base)
        await approval.send_for_approval("tomas", "integ-001", job_dir)

    # Проверяем что флаг создан
    assert (job_dir / "approval_sent.flag").exists(), (
        "approval_sent.flag должен появиться после отправки"
    )


try:
    asyncio.run(run_test())
finally:
    shutil.rmtree(base, ignore_errors=True)

print("✅ integration flow OK")

