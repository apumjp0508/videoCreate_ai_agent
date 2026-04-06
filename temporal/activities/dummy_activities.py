"""
ダミー Activity 実装。interfaces.py の契約を満たす。

本番実装に置き換えるときは同じ @activity.defn(name="...") を持つ
別ファイルを作り、worker.py の登録先を差し替えるだけでよい。
"""
import asyncio
import logging

from temporalio import activity

from temporal.activities.interfaces import (
    ScriptGenerationInput,
    ScriptGenerationOutput,
    VideoGenerationInput,
    VideoGenerationOutput,
    YoutubeUploadInput,
    YoutubeUploadOutput,
)

logger = logging.getLogger(__name__)


@activity.defn(name="generate_video_script")
async def dummy_generate_video_script(input: ScriptGenerationInput) -> ScriptGenerationOutput:
    logger.info(
        "[Dummy] generate_video_script  job_id=%s  prompt_id=%s",
        input.job_id, input.prompt_id,
    )
    await asyncio.sleep(0.1)
    return ScriptGenerationOutput(
        script_text=f"[DUMMY SCRIPT]  job_id={input.job_id}  prompt_id={input.prompt_id}",
    )


@activity.defn(name="generate_video")
async def dummy_generate_video(input: VideoGenerationInput) -> VideoGenerationOutput:
    logger.info(
        "[Dummy] generate_video  job_id=%s  config_id=%s",
        input.job_id, input.video_ai_config_id,
    )
    await asyncio.sleep(0.1)
    return VideoGenerationOutput(
        video_url=f"https://storage.example.com/videos/{input.job_id}.mp4",
    )


@activity.defn(name="upload_to_youtube")
async def dummy_upload_to_youtube(input: YoutubeUploadInput) -> YoutubeUploadOutput:
    logger.info(
        "[Dummy] upload_to_youtube  job_id=%s  channel=%s  mode=%s",
        input.job_id, input.youtube_channel_id, input.publish_mode,
    )
    await asyncio.sleep(0.1)
    yt_id = f"dummy_yt_{input.job_id[:8]}"
    return YoutubeUploadOutput(
        youtube_video_id=yt_id,
        youtube_video_url=f"https://www.youtube.com/watch?v={yt_id}",
    )
