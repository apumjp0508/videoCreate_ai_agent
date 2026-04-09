"""
VideoPipelineWorkflow 用 Worker エントリポイント。

起動方法:
    python -m temporal.worker_pipeline

登録内容:
  Workflows:
    - VideoPipelineWorkflow     (親)
    - VideoGenerationWorkflow   (子)
    - YoutubePublishWorkflow    (子)

  Activities  ─ video_generation（DjangoVideoGenerationService）:
    - fetch_materials          ← Django ORM
    - fetch_ai_config          ← Django ORM
    - fetch_request_definition ← Django ORM
    - build_ai_request         ← 純粋ロジック
    - submit_ai_request        ← Dummy（AIプロバイダー固有: 差し替え必要）
    - poll_generation_status   ← Dummy（AIプロバイダー固有: 差し替え必要）
    - fetch_generated_video    ← Dummy（AIプロバイダー固有: 差し替え必要）

  Activities  ─ video_metadata（Dummy: AI プロバイダー固有）:
    - analyze_video_content    ← Dummy（差し替え必要）
    - generate_video_metadata  ← Dummy（差し替え必要）

  Activities  ─ job_progress（Django ORM）:
    - update_job_progress      ← VideoJob.current_step + VideoJobEvent 更新

  Activities  ─ thumbnail_generation（OpenAI GPT-4o Vision）:
    - generate_thumbnail       ← ffmpeg スナップショット + GPT-4o Vision スコアリング

  Activities  ─ youtube_publish（DjangoYoutubePublishService + YoutubeDataApiService）:
    - fetch_youtube_account    ← Django ORM
    - fetch_oauth_token        ← Django ORM + Fernet 復号
    - refresh_access_token     ← Google OAuth API + DB 更新
    - fetch_publish_settings   ← Django ORM + AI 生成オーバーライド
    - build_upload_request     ← 純粋ロジック
    - upload_video_to_youtube  ← YouTube Data API v3
    - set_thumbnail            ← YouTube Data API v3
    - apply_publish_settings   ← YouTube Data API v3
    - save_publish_result      ← Django ORM

サービス差し替え方法:
  AIプロバイダー固有の Activity は dummy モジュールの _service を上書きする。

  例（Runway 実装に差し替える場合）:
    from temporal.activities.video_generation import dummy as vg_dummy
    from myapp.services.runway import RunwayVideoGenerationService
    vg_dummy._service = RunwayVideoGenerationService()
"""
import asyncio
import logging
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from django.conf import settings  # noqa: E402
from temporalio.worker import Worker  # noqa: E402

# ─────────────────────────────────────────────────────────────
# サービス注入: APP_ENV に応じて dummy/本サービスを自動選択
# ─────────────────────────────────────────────────────────────
from temporal.service_registry import configure_services  # noqa: E402

_active_env = configure_services()
logger.info("service_registry applied  env=%s", _active_env)

# ─────────────────────────────────────────────────────────────
# Activity 関数インポート（サービス注入後に行う）
# ─────────────────────────────────────────────────────────────
from temporal.activities.job_progress.dummy import (  # noqa: E402
    dummy_update_job_progress,
)
from temporal.activities.video_generation.dummy import (  # noqa: E402
    dummy_build_ai_request,
    dummy_fetch_ai_config,
    dummy_fetch_generated_video,
    dummy_fetch_materials,
    dummy_fetch_request_definition,
    dummy_poll_generation_status,
    dummy_save_generated_video,
    dummy_submit_ai_request,
)
from temporal.activities.video_metadata.dummy import (  # noqa: E402
    dummy_analyze_video_content,
    dummy_generate_video_metadata,
)
from temporal.activities.thumbnail_generation.dummy import (  # noqa: E402
    dummy_generate_thumbnail,
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

# ─────────────────────────────────────────────────────────────
# Workflow 登録
# ─────────────────────────────────────────────────────────────
from temporal.client import get_temporal_client  # noqa: E402
from temporal.workflows.pipeline.video_generation_workflow import VideoGenerationWorkflow  # noqa: E402
from temporal.workflows.pipeline.video_pipeline_workflow import VideoPipelineWorkflow  # noqa: E402
from temporal.workflows.pipeline.youtube_publish_workflow import YoutubePublishWorkflow  # noqa: E402

# ─────────────────────────────────────────────────────────────
# Activity リスト（追加・差し替えはここで行う）
# ─────────────────────────────────────────────────────────────

JOB_PROGRESS_ACTIVITIES = [
    dummy_update_job_progress,   # Django 実装: current_step / VideoJobEvent 更新
]

VIDEO_GENERATION_ACTIVITIES = [
    dummy_fetch_materials,
    dummy_fetch_ai_config,
    dummy_fetch_request_definition,
    dummy_build_ai_request,
    dummy_submit_ai_request,        # Dummy: AIプロバイダー固有
    dummy_poll_generation_status,   # Dummy: AIプロバイダー固有
    dummy_fetch_generated_video,    # Dummy: AIプロバイダー固有
    dummy_save_generated_video,     # Django 実装: 動画を media に保存 + GeneratedVideo 作成
]

VIDEO_METADATA_ACTIVITIES = [
    dummy_analyze_video_content,    # Dummy: AIプロバイダー固有
    dummy_generate_video_metadata,  # Dummy: AIプロバイダー固有
]

THUMBNAIL_GENERATION_ACTIVITIES = [
    dummy_generate_thumbnail,       # Dummy: AIプロバイダー固有
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
            *JOB_PROGRESS_ACTIVITIES,
            *VIDEO_GENERATION_ACTIVITIES,
            *VIDEO_METADATA_ACTIVITIES,
            *THUMBNAIL_GENERATION_ACTIVITIES,
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
