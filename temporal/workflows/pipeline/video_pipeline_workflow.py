"""
VideoPipelineWorkflow  ─ 動画生成〜YouTube投稿を統括する親 Workflow。

責務（これだけ）:
  1. VideoGenerationWorkflow（子）を実行して動画 URL を得る
  2. YoutubePublishWorkflow（子）を実行して YouTube に投稿する
  3. 最終結果を返す

この Workflow は「全体の流れを制御する」だけであり、
Activity を直接呼び出したり、業務ロジックを持たない。
処理の詳細はすべて子 Workflow に委譲する。

入力:  PipelineInput  (temporal/pipeline_types.py)
出力:  PipelineOutput (temporal/pipeline_types.py)
"""
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from temporal.pipeline_types import (
        PipelineInput,
        PipelineOutput,
        VideoGenerationWorkflowInput,
        YoutubePublishWorkflowInput,
    )
    from temporal.workflows.pipeline.video_generation_workflow import VideoGenerationWorkflow
    from temporal.workflows.pipeline.youtube_publish_workflow import YoutubePublishWorkflow

# 子 Workflow のタスクキューは親と同じものを使う（変更するなら定数化する）
_TASK_QUEUE = None  # None = workflow.info().task_queue（実行時に解決）


@workflow.defn
class VideoPipelineWorkflow:
    """
    親 Workflow。動画生成〜YouTube投稿のパイプラインを統括する。

    子 Workflow の呼び出し順:
      1. VideoGenerationWorkflow  ─ 動画を生成して URL を返す
      2. YoutubePublishWorkflow   ─ 動画を YouTube へ投稿して結果を返す

    この Workflow を追加・変更するとき:
      - 子 Workflow の追加・差し替えはここに書く
      - 業務ロジック（API 呼び出し・DB 操作）は書かない
      - Activity の直接呼び出しは避け、子 Workflow に任せる
    """

    @workflow.run
    async def run(self, input: PipelineInput) -> PipelineOutput:
        workflow.logger.info(
            "VideoPipelineWorkflow started  job_id=%s  user_id=%s  channel=%s",
            input.job_id, input.user_id, input.youtube_channel_id,
        )

        task_queue = workflow.info().task_queue

        # ── Phase 1: 動画生成 ─────────────────────────────────────
        # VideoGenerationWorkflow に動画生成をすべて委譲する
        workflow.logger.info("Starting VideoGenerationWorkflow  job_id=%s", input.job_id)
        video_gen_result = await workflow.execute_child_workflow(
            VideoGenerationWorkflow.run,
            VideoGenerationWorkflowInput(
                job_id=input.job_id,
                user_id=input.user_id,
                video_ai_config_id=input.video_ai_config_id,
                prompt_id=input.prompt_id,
                image_ids=input.image_ids,
                audio_ids=input.audio_ids,
            ),
            id=f"{input.job_id}-video-gen",
            task_queue=task_queue,
            execution_timeout=timedelta(hours=2),
        )
        workflow.logger.info(
            "VideoGenerationWorkflow completed  job_id=%s  video_url=%s",
            input.job_id, video_gen_result.video_url,
        )

        # ── Phase 2: YouTube 投稿 ─────────────────────────────────
        # YoutubePublishWorkflow に投稿をすべて委譲する
        workflow.logger.info("Starting YoutubePublishWorkflow  job_id=%s", input.job_id)
        publish_result = await workflow.execute_child_workflow(
            YoutubePublishWorkflow.run,
            YoutubePublishWorkflowInput(
                job_id=input.job_id,
                user_id=input.user_id,
                video_url=video_gen_result.video_url,
                oauth_record_id=input.oauth_record_id,
                youtube_channel_id=input.youtube_channel_id,
                publish_mode=input.publish_mode,
                thumbnail_url=input.thumbnail_url,
                title=input.title,
                description=input.description,
                tags=input.tags,
            ),
            id=f"{input.job_id}-yt-publish",
            task_queue=task_queue,
            execution_timeout=timedelta(hours=1),
        )
        workflow.logger.info(
            "YoutubePublishWorkflow completed  job_id=%s  yt_id=%s",
            input.job_id, publish_result.youtube_video_id,
        )

        # ── 完了 ──────────────────────────────────────────────────
        workflow.logger.info(
            "VideoPipelineWorkflow completed  job_id=%s  yt_url=%s",
            input.job_id, publish_result.youtube_video_url,
        )
        return PipelineOutput(
            job_id=input.job_id,
            youtube_video_id=publish_result.youtube_video_id,
            youtube_video_url=publish_result.youtube_video_url,
        )
