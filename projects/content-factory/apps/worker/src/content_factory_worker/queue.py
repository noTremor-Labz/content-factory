from typing import Any

from dramatiq.message import Message

from content_factory_worker.broker import configure_broker
from content_factory_worker.config import get_worker_settings


def enqueue_render_job(render_job_id: str) -> Message[Any]:
    broker = configure_broker(get_worker_settings())
    from content_factory_worker.jobs.render import process_render_job_message

    process_render_job_message.broker = broker
    broker.declare_actor(process_render_job_message)
    return process_render_job_message.send(render_job_id)
