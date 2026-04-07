"""
VideoMetadata Activity のダミー実装。

構成:
  - DummyVideoMetadataService : VideoMetadataServiceProtocol のダミー実装
  - dummy_* 関数群            : @activity.defn(name=...) で登録する Activity 関数
    各関数は DummyVideoMetadataService に処理を委譲する

差し替え方:
  本番実装では RealVideoMetadataService を作り、
  worker_pipeline.py の _service = の部分を差し替えるだけでよい。
"""
import asyncio
import logging

from temporalio import activity

from temporal.activities.video_metadata.interfaces import (
    AnalyzeVideoContentInput,
    AnalyzeVideoContentOutput,
    GenerateVideoMetadataInput,
    GenerateVideoMetadataOutput,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# ダミーサービス実装
# ─────────────────────────────────────────────────────────────

class DummyVideoMetadataService:
    """
    VideoMetadataServiceProtocol のダミー実装。
    すべてのメソッドが固定値を返す。
    本番実装に切り替えるときはこのクラスを同 Protocol 準拠クラスに差し替える。
    """

    async def analyze_video_content(
        self,
        input: AnalyzeVideoContentInput,
    ) -> AnalyzeVideoContentOutput:
        logger.info("[Dummy] analyze_video_content  job_id=%s  url=%s", input.job_id, input.video_url)
        await asyncio.sleep(0.05)
        return AnalyzeVideoContentOutput(
            summary=(
                "[DUMMY] This video showcases engaging content with dynamic visuals. "
                "It features a clear narrative flow and professional presentation style."
            ),
            detected_topics=["technology", "education", "tutorial"],
        )

    async def generate_video_metadata(
        self,
        input: GenerateVideoMetadataInput,
    ) -> GenerateVideoMetadataOutput:
        logger.info(
            "[Dummy] generate_video_metadata  job_id=%s  lang=%s",
            input.job_id, input.language,
        )
        await asyncio.sleep(0.05)
        return GenerateVideoMetadataOutput(
            title=f"[DUMMY] 動画タイトル（job: {input.job_id[:8]}）",
            description=(
                f"[DUMMY] この動画は以下のプロンプトをもとに生成されました。\n\n"
                f"プロンプト: {input.prompt_text[:100]}...\n\n"
                f"要約: {input.video_summary[:200]}"
            ),
            tags=["dummy", "AI生成", "自動生成"],
            category="Entertainment",
        )


# ─────────────────────────────────────────────────────────────
# Activity 関数（worker_pipeline.py で登録する）
# ─────────────────────────────────────────────────────────────

_service = DummyVideoMetadataService()


@activity.defn(name="analyze_video_content")
async def dummy_analyze_video_content(
    input: AnalyzeVideoContentInput,
) -> AnalyzeVideoContentOutput:
    return await _service.analyze_video_content(input)


@activity.defn(name="generate_video_metadata")
async def dummy_generate_video_metadata(
    input: GenerateVideoMetadataInput,
) -> GenerateVideoMetadataOutput:
    return await _service.generate_video_metadata(input)
