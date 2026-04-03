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

from router import parse_callback_data  # noqa: E402


action, blogger, job_id, channel_type = parse_callback_data("approve:tomas:job-001:food")
assert action == "approve", f"action: {action}"
assert blogger == "tomas", f"blogger: {blogger}"
assert job_id == "job-001", f"job_id: {job_id}"
assert channel_type == "food", f"channel_type: {channel_type}"

action, blogger, job_id, channel_type = parse_callback_data(
    "revise:misha:2024-01-15-morning:food",
)
assert action == "revise"
assert blogger == "misha"
assert job_id == "2024-01-15-morning"
assert channel_type == "food"

action, blogger, job_id, channel_type = parse_callback_data("reject:yulya:abc123:food")
assert action == "reject"
assert blogger == "yulya"
assert channel_type == "food"

print("✅ router callback parsing OK")

