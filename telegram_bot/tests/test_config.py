import os
import sys
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

import config  # noqa: E402


assert set(config.BLOGGERS.keys()) == {"tomas", "misha", "yulya", "nasik"}, (
    "BLOGGERS должен содержать 4 блогера, "
    f"получили: {list(config.BLOGGERS.keys())}"
)

for blogger, data in config.BLOGGERS.items():
    assert "channels" in data, f"У блогера {blogger} нет ключа 'channels'"
    if blogger == "tomas":
        assert "food" in data["channels"], "У tomas нет food channel"
        assert data["channels"]["food"], "У tomas пустой food channel_id"
        assert "vibe" in data["channels"], "У tomas нет vibe channel"
        assert data["channels"]["vibe"], "У tomas пустой vibe channel_id"
    else:
        assert data["channels"] == {}, f"У блогера {blogger} должны быть пустые channels"

assert hasattr(config, "STUCK_THRESHOLD_HOURS"), "Нет STUCK_THRESHOLD_HOURS"
assert isinstance(config.STUCK_THRESHOLD_HOURS, (int, float)), (
    "STUCK_THRESHOLD_HOURS должен быть числом"
)

assert hasattr(config, "SHARED_BASE_PATH"), "Нет SHARED_BASE_PATH"


print("✅ config.py OK")

