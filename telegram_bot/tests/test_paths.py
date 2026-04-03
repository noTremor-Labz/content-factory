import os
import sys

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

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import paths_util  # noqa: E402

p1 = paths_util.get_job_dir("tomas", "job-001")
assert str(p1).endswith(
    "bloggers/tomas/jobs/job-001"
), f"Неверный путь: {p1}"

p = Path("/shared/bloggers/misha/jobs/job-002/ready.md")
blogger = paths_util.extract_blogger(p)
assert blogger == "misha", f"Ожидали 'misha', получили '{blogger}'"

job_id = paths_util.extract_job_id(p)
assert job_id == "job-002", f"Ожидали 'job-002', получили '{job_id}'"


print("✅ paths_util.py OK")

