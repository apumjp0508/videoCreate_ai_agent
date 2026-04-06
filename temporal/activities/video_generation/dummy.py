"""
VideoGeneration Activity のダミー実装。

構成:
  - DummyVideoGenerationService: VideoGenerationServiceProtocol のダミー実装
  - dummy_* 関数群: @activity.defn(name=...) で登録する Activity 関数
    各関数は DummyVideoGenerationService に処理を委譲する

差し替え方:
  本番実装では RealVideoGenerationService を作り、
  worker_pipeline.py の _service = の部分を差し替えるだけでよい。
"""
import asyncio
import logging

from temporalio import activity

from temporal.activities.video_generation.interfaces import (
    BuildAiRequestInput,
    BuildAiRequestOutput,
    FetchAiConfigInput,
    FetchAiConfigOutput,
    FetchGeneratedVideoInput,
    FetchGeneratedVideoOutput,
    FetchMaterialsInput,
    FetchMaterialsOutput,
    FetchRequestDefinitionInput,
    FetchRequestDefinitionOutput,
    PollGenerationStatusInput,
    PollGenerationStatusOutput,
    SubmitAiRequestInput,
    SubmitAiRequestOutput,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# ダミーサービス実装
# ─────────────────────────────────────────────────────────────

class DummyVideoGenerationService:
    """
    VideoGenerationServiceProtocol のダミー実装。
    すべてのメソッドが固定値を返す。
    本番実装に切り替えるときはこのクラスを同 Protocol 準拠クラスに差し替える。
    """

    async def fetch_materials(self, input: FetchMaterialsInput) -> FetchMaterialsOutput:
        logger.info("[Dummy] fetch_materials  job_id=%s", input.job_id)
        await asyncio.sleep(0.05)
        return FetchMaterialsOutput(
            image_ids=input.image_ids or [1, 2],
            audio_ids=input.audio_ids or [10],
            metadata={"source": "dummy"},
        )

    async def fetch_ai_config(self, input: FetchAiConfigInput) -> FetchAiConfigOutput:
        logger.info("[Dummy] fetch_ai_config  job_id=%s  config_id=%s", input.job_id, input.video_ai_config_id)
        await asyncio.sleep(0.05)
        return FetchAiConfigOutput(
            config_id=input.video_ai_config_id,
            model_name="dummy-video-model-v1",
            api_endpoint="https://api.dummy-ai.example.com/v1/generate",
            params={"quality": "high", "duration": 60},
        )

    async def fetch_request_definition(self, input: FetchRequestDefinitionInput) -> FetchRequestDefinitionOutput:
        logger.info("[Dummy] fetch_request_definition  job_id=%s  prompt_id=%s", input.job_id, input.prompt_id)
        await asyncio.sleep(0.05)
        return FetchRequestDefinitionOutput(
            prompt_id=input.prompt_id,
            prompt_text=f"[DUMMY PROMPT] id={input.prompt_id} / Create an engaging video about this topic.",
            format_settings={"aspect_ratio": "16:9", "style": "cinematic"},
        )

    async def build_ai_request(self, input: BuildAiRequestInput) -> BuildAiRequestOutput:
        logger.info("[Dummy] build_ai_request  job_id=%s  model=%s", input.job_id, input.model_name)
        await asyncio.sleep(0.05)
        return BuildAiRequestOutput(
            ai_request_payload={
                "model": input.model_name,
                "prompt": input.prompt_text,
                "image_ids": input.image_ids,
                "audio_ids": input.audio_ids,
                "params": input.config_params,
                "format": input.format_settings,
            }
        )

    async def submit_ai_request(self, input: SubmitAiRequestInput) -> SubmitAiRequestOutput:
        logger.info("[Dummy] submit_ai_request  job_id=%s", input.job_id)
        await asyncio.sleep(0.05)
        return SubmitAiRequestOutput(
            generation_id=f"gen_{input.job_id[:8]}",
            initial_status="pending",
        )

    async def poll_generation_status(self, input: PollGenerationStatusInput) -> PollGenerationStatusOutput:
        logger.info("[Dummy] poll_generation_status  job_id=%s  gen_id=%s", input.job_id, input.generation_id)
        await asyncio.sleep(0.05)
        # ダミーは常に即座に完了を返す
        return PollGenerationStatusOutput(
            generation_id=input.generation_id,
            status="completed",
            is_complete=True,
            video_url=f"https://storage.dummy.example.com/videos/{input.generation_id}.mp4",
        )

    async def fetch_generated_video(self, input: FetchGeneratedVideoInput) -> FetchGeneratedVideoOutput:
        logger.info("[Dummy] fetch_generated_video  job_id=%s  gen_id=%s", input.job_id, input.generation_id)
        await asyncio.sleep(0.05)
        return FetchGeneratedVideoOutput(
            video_url=input.video_url,
            video_metadata={
                "duration_sec": 60,
                "resolution": "1920x1080",
                "format": "mp4",
                "size_bytes": 50_000_000,
            },
        )


# ─────────────────────────────────────────────────────────────
# Activity 関数（worker_pipeline.py で登録する）
# 各関数はサービスに処理を委譲するだけ
# ─────────────────────────────────────────────────────────────

_service = DummyVideoGenerationService()


@activity.defn(name="fetch_materials")
async def dummy_fetch_materials(input: FetchMaterialsInput) -> FetchMaterialsOutput:
    return await _service.fetch_materials(input)


@activity.defn(name="fetch_ai_config")
async def dummy_fetch_ai_config(input: FetchAiConfigInput) -> FetchAiConfigOutput:
    return await _service.fetch_ai_config(input)


@activity.defn(name="fetch_request_definition")
async def dummy_fetch_request_definition(
    input: FetchRequestDefinitionInput,
) -> FetchRequestDefinitionOutput:
    return await _service.fetch_request_definition(input)


@activity.defn(name="build_ai_request")
async def dummy_build_ai_request(input: BuildAiRequestInput) -> BuildAiRequestOutput:
    return await _service.build_ai_request(input)


@activity.defn(name="submit_ai_request")
async def dummy_submit_ai_request(input: SubmitAiRequestInput) -> SubmitAiRequestOutput:
    return await _service.submit_ai_request(input)


@activity.defn(name="poll_generation_status")
async def dummy_poll_generation_status(
    input: PollGenerationStatusInput,
) -> PollGenerationStatusOutput:
    return await _service.poll_generation_status(input)


@activity.defn(name="fetch_generated_video")
async def dummy_fetch_generated_video(
    input: FetchGeneratedVideoInput,
) -> FetchGeneratedVideoOutput:
    return await _service.fetch_generated_video(input)
