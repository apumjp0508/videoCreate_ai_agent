"""
Temporal Worker エントリポイント。

起動方法:
    python -m temporal.worker
"""
import asyncio
import logging
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from temporalio.worker import Worker  # noqa: E402

from temporal.activities.dummy_activities import (  # noqa: E402
    generate_video,
    generate_video_script,
    upload_to_youtube,
)
from temporal.client import get_temporal_client  # noqa: E402
from temporal.workflows.video_job_workflow import VideoJobWorkflow  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    client = await get_temporal_client()
    async with Worker(
        client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        workflows=[VideoJobWorkflow],
        activities=[generate_video_script, generate_video, upload_to_youtube],
    ):
        logger.info(
            "Worker started  task_queue=%s  namespace=%s  host=%s",
            settings.TEMPORAL_TASK_QUEUE,
            settings.TEMPORAL_NAMESPACE,
            settings.TEMPORAL_HOST,
        )
        await asyncio.get_event_loop().create_future()


if __name__ == "__main__":
    asyncio.run(main())
