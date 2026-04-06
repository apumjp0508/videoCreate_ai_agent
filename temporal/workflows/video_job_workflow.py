"""
VideoJob Workflow。

Workflow は interfaces.py の Activity スタブだけを参照する。
実装（dummy / 本番）は worker.py で差し替える。

入力:  VideoJobInput  (temporal/types.py)
出力:  VideoJobOutput (temporal/types.py)
"""
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from temporal.activities.interfaces import (
        ScriptGenerationInput,
        VideoGenerationInput,
        YoutubeUploadInput,
        generate_video,
        generate_video_script,
        upload_to_youtube,
    )
    from temporal.types import VideoJobInput, VideoJobOutput


@workflow.defn
class VideoJobWorkflow:
    @workflow.run
    async def run(self, input: VideoJobInput) -> VideoJobOutput:
        workflow.logger.info(
            "VideoJobWorkflow started  job_id=%s  user_id=%s",
            input.job_id, input.user_id,
        )

        # Step 1: スクリプト生成
        script_result = await workflow.execute_activity(
            generate_video_script,
            ScriptGenerationInput(
                job_id=input.job_id,
                prompt_id=input.prompt_id,
            ),
            start_to_close_timeout=timedelta(minutes=5),
        )
        workflow.logger.info("Script generated  job_id=%s", input.job_id)

        # Step 2: 動画生成
        video_result = await workflow.execute_activity(
            generate_video,
            VideoGenerationInput(
                job_id=input.job_id,
                script_text=script_result.script_text,
                video_ai_config_id=input.video_ai_config_id,
                image_ids=input.image_ids,
                audio_ids=input.audio_ids,
            ),
            start_to_close_timeout=timedelta(minutes=30),
        )
        workflow.logger.info(
            "Video generated  job_id=%s  url=%s", input.job_id, video_result.video_url,
        )

        # Step 3: YouTube アップロード
        youtube_result = await workflow.execute_activity(
            upload_to_youtube,
            YoutubeUploadInput(
                job_id=input.job_id,
                video_url=video_result.video_url,
                oauth_record_id=input.oauth_record_id,
                youtube_channel_id=input.youtube_channel_id,
                publish_mode=input.publish_mode,
            ),
            start_to_close_timeout=timedelta(minutes=10),
        )
        workflow.logger.info(
            "Uploaded to YouTube  job_id=%s  yt_id=%s",
            input.job_id, youtube_result.youtube_video_id,
        )

        return VideoJobOutput(
            job_id=input.job_id,
            youtube_video_id=youtube_result.youtube_video_id,
            youtube_video_url=youtube_result.youtube_video_url,
        )
