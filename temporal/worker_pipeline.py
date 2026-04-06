"""
VideoPipelineWorkflow 用 Worker エントリポイント。

起動方法:
    python -m temporal.worker_pipeline

登録内容:
  Workflows:
    - VideoPipelineWorkflow     (親)
    - VideoGenerationWorkflow   (子)
    - YoutubePublishWorkflow    (子)

  Activities  ─ video_generation:
    - dummy_fetch_materials
    - dummy_fetch_ai_config
    - dummy_fetch_request_definition
    - dummy_build_ai_request
    - dummy_submit_ai_request
    - dummy_poll_generation_status
    - dummy_fetch_generated_video

  Activities  ─ youtube_publish:
    - dummy_fetch_youtube_account
    - dummy_fetch_oauth_token
    - dummy_refresh_access_token
    - dummy_fetch_publish_settings
    - dummy_build_upload_request
    - dummy_upload_video_to_youtube
    - dummy_set_thumbnail
    - dummy_apply_publish_settings
    - dummy_save_publish_result

サービス差し替え方法:
  本番実装に切り替えるには、各 dummy.py の _service = の行を
  本番サービスクラスのインスタンスに変更するか、
  このファイルで dummy モジュールの _service を上書きする。

  例:
    from temporal.activities.video_generation import dummy as vg_dummy
    from myapp.services.video_generation import RealVideoGenerationService
    vg_dummy._service = RealVideoGenerationService()
"""
import asyncio
import logging
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from temporalio.worker import Worker  # noqa: E402

# ── Activity 実装（ダミー） ───────────────────────────────────
from temporal.activities.video_generation.dummy import (  # noqa: E402
    dummy_build_ai_request,
    dummy_fetch_ai_config,
    dummy_fetch_generated_video,
    dummy_fetch_materials,
    dummy_fetch_request_definition,
    dummy_poll_generation_status,
    dummy_submit_ai_request,
)
from temporal.activities.youtube_publish.dummy import (  # noqa: E402
    dummy_apply_publish_settings,
    dummy_build_upload_request,
    dummy_fetch_oauth_token,
    dummy_fetch_publish_settings,
    dummy_fetch_youtube_account,
    dummy_refresh_access_token,
    dummy_save_publish_result,
    dummy_set_thumbnail,
    dummy_upload_video_to_youtube,
)

# ── Workflow 登録 ─────────────────────────────────────────────
from temporal.client import get_temporal_client  # noqa: E402
from temporal.workflows.pipeline.video_generation_workflow import VideoGenerationWorkflow  # noqa: E402
from temporal.workflows.pipeline.video_pipeline_workflow import VideoPipelineWorkflow  # noqa: E402
from temporal.workflows.pipeline.youtube_publish_workflow import YoutubePublishWorkflow  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Activity リスト
# 追加・差し替えはここで行う
# ─────────────────────────────────────────────────────────────

VIDEO_GENERATION_ACTIVITIES = [
    dummy_fetch_materials,
    dummy_fetch_ai_config,
    dummy_fetch_request_definition,
    dummy_build_ai_request,
    dummy_submit_ai_request,
    dummy_poll_generation_status,
    dummy_fetch_generated_video,
]

YOUTUBE_PUBLISH_ACTIVITIES = [
    dummy_fetch_youtube_account,
    dummy_fetch_oauth_token,
    dummy_refresh_access_token,
    dummy_fetch_publish_settings,
    dummy_build_upload_request,
    dummy_upload_video_to_youtube,
    dummy_set_thumbnail,
    dummy_apply_publish_settings,
    dummy_save_publish_result,
]


async def main() -> None:
    client = await get_temporal_client()

    async with Worker(
        client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        workflows=[
            VideoPipelineWorkflow,
            VideoGenerationWorkflow,
            YoutubePublishWorkflow,
        ],
        activities=[
            *VIDEO_GENERATION_ACTIVITIES,
            *YOUTUBE_PUBLISH_ACTIVITIES,
        ],
    ):
        logger.info(
            "Pipeline Worker started  task_queue=%s  namespace=%s  host=%s",
            settings.TEMPORAL_TASK_QUEUE,
            settings.TEMPORAL_NAMESPACE,
            settings.TEMPORAL_HOST,
        )
        await asyncio.get_event_loop().create_future()


if __name__ == "__main__":
    asyncio.run(main())
