"""
ThumbnailGeneration Activity のダミー実装。

構成:
  - DummyThumbnailService : ThumbnailGenerationServiceProtocol のダミー実装
  - dummy_* 関数群        : @activity.defn(name=...) で登録する Activity 関数
    各関数は DummyThumbnailService に処理を委譲する

差し替え方:
  本番実装では RealThumbnailService を作り、
  worker_pipeline.py の _service = の部分を差し替えるだけでよい。
"""
import asyncio
import logging

from temporalio import activity

from temporal.activities.thumbnail_generation.interfaces import (
    GenerateThumbnailInput,
    GenerateThumbnailOutput,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# ダミーサービス実装
# ─────────────────────────────────────────────────────────────

class DummyThumbnailService:
    """
    ThumbnailGenerationServiceProtocol のダミー実装。
    固定のプレースホルダー URL を返す。
    本番実装に切り替えるときはこのクラスを同 Protocol 準拠クラスに差し替える。
    """

    async def generate_thumbnail(
        self,
        input: GenerateThumbnailInput,
    ) -> GenerateThumbnailOutput:
        logger.info(
            "[Dummy] generate_thumbnail  job_id=%s  title=%s  style=%s",
            input.job_id, input.title, input.style,
        )
        await asyncio.sleep(0.05)
        return GenerateThumbnailOutput(
            thumbnail_url=f"https://placehold.co/1280x720?text=DUMMY+THUMBNAIL",
            metadata={
                "width": 1280,
                "height": 720,
                "format": "png",
                "generated_by": "dummy",
            },
        )


# ─────────────────────────────────────────────────────────────
# Activity 関数（worker_pipeline.py で登録する）
# ─────────────────────────────────────────────────────────────

_service = DummyThumbnailService()


@activity.defn(name="generate_thumbnail")
async def dummy_generate_thumbnail(
    input: GenerateThumbnailInput,
) -> GenerateThumbnailOutput:
    return await _service.generate_thumbnail(input)
