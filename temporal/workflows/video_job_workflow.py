"""
VideoJob Workflow。
3 つの Activity を順に実行して動画 1 本を完成させる。

入力:  VideoJobParams
出力:  VideoJobResult (youtube_video_id が入る)
"""
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from temporal.activities.dummy_activities import (
        generate_video,
        generate_video_script,
        upload_to_youtube,
    )


@dataclass
class VideoJobParams:
    job_id: str
    prompt: str


@dataclass
class VideoJobResult:
    job_id: str
    youtube_video_id: str


@workflow.defn
class VideoJobWorkflow:
    @workflow.run
    async def run(self, params: VideoJobParams) -> VideoJobResult:
        workflow.logger.info("VideoJobWorkflow started job_id=%s", params.job_id)

        # Step 1: スクリプト生成
        script = await workflow.execute_activity(
            generate_video_script,
            args=[params.job_id, params.prompt],
            start_to_close_timeout=timedelta(minutes=5),
        )
        workflow.logger.info("Script generated job_id=%s", params.job_id)

        # Step 2: 動画生成
        video_url = await workflow.execute_activity(
            generate_video,
            args=[params.job_id, script],
            start_to_close_timeout=timedelta(minutes=30),
        )
        workflow.logger.info("Video generated job_id=%s url=%s", params.job_id, video_url)

        # Step 3: YouTube アップロード
        youtube_video_id = await workflow.execute_activity(
            upload_to_youtube,
            args=[params.job_id, video_url],
            start_to_close_timeout=timedelta(minutes=10),
        )
        workflow.logger.info(
            "Uploaded to YouTube job_id=%s yt_id=%s", params.job_id, youtube_video_id
        )

        return VideoJobResult(job_id=params.job_id, youtube_video_id=youtube_video_id)
