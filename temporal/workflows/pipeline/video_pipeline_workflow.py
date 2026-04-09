"""
VideoPipelineWorkflow  ─ 動画生成〜YouTube投稿を統括する親 Workflow。

責務（これだけ）:
  1. VideoGenerationWorkflow（子）を実行して動画 URL を得る
  2. YoutubePublishWorkflow（子）を実行して YouTube に投稿する
  3. 最終結果を返す
  4. いずれかのフェーズで失敗した場合は Django DB に記録して再送出する

この Workflow は「全体の流れを制御する」だけであり、
Activity を直接呼び出したり、業務ロジックを持たない。
処理の詳細はすべて子 Workflow に委譲する。

入力:  PipelineInput  (temporal/pipeline_types.py)
出力:  PipelineOutput (temporal/pipeline_types.py)
"""
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from temporal.activities.job_progress.interfaces import (
        UpdateJobProgressInput,
        update_job_progress,
    )
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

        # 失敗時にどのフェーズで落ちたかを Django 側に伝えるための変数
        _failed_phase = "UNKNOWN"

        try:
            # ── Phase 1: 動画生成 ─────────────────────────────────────
            # VideoGenerationWorkflow に動画生成をすべて委譲する
            _failed_phase = "VIDEO_GENERATION"
            workflow.logger.info("Starting VideoGenerationWorkflow  job_id=%s", input.job_id)
            video_gen_result = await workflow.execute_child_workflow(
                VideoGenerationWorkflow.run,
                VideoGenerationWorkflowInput(
                    job_id=input.job_id,
                    user_id=input.user_id,
                    credential_id=input.credential_id,
                    model_id=input.model_id,
                    prompt_id=input.prompt_id,
                    image_ids=input.image_ids,
                    audio_ids=input.audio_ids,
                    video_length=input.video_length,
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
            _failed_phase = "YOUTUBE_PUBLISH"
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
                    prompt_id=input.prompt_id,
                ),
                id=f"{input.job_id}-yt-publish",
                task_queue=task_queue,
                execution_timeout=timedelta(hours=1),
            )
            workflow.logger.info(
                "YoutubePublishWorkflow completed  job_id=%s  yt_id=%s",
                input.job_id, publish_result.youtube_video_id,
            )

        except Exception as exc:
            # ── 失敗時: Django DB にエラー情報を書き込んで再送出 ──────
            # エラーの根本原因を取り出す（ChildWorkflowError でラップされている場合）
            root_cause = _unwrap_cause(exc)
            error_summary = f"[{_failed_phase}] {type(root_cause).__name__}: {root_cause}"

            workflow.logger.error(
                "VideoPipelineWorkflow FAILED  job_id=%s  phase=%s  error=%s",
                input.job_id, _failed_phase, error_summary,
            )

            # update_job_progress Activity でステータスと失敗イベントを DB に書き込む
            # start_to_close_timeout は短めに設定して無限待ちを防ぐ
            try:
                await workflow.execute_activity(
                    update_job_progress,
                    UpdateJobProgressInput(
                        job_id=input.job_id,
                        step=_failed_phase,
                        event_type="JOB_FAILED",
                        message=error_summary,
                        status="failed",
                        payload={
                            "failed_phase":     _failed_phase,
                            "error_type":       type(root_cause).__name__,
                            "error_detail":     str(root_cause),
                            # 原因の連鎖を保持（開発環境でのデバッグ用）
                            "cause_chain":      _build_cause_chain(exc),
                        },
                    ),
                    start_to_close_timeout=timedelta(minutes=2),
                )
            except Exception as progress_exc:
                # 失敗記録自体が失敗しても元の例外を優先して送出する
                workflow.logger.error(
                    "update_job_progress also failed  job_id=%s  err=%s",
                    input.job_id, progress_exc,
                )

            raise  # Temporal にも失敗として記録させる

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


# ─────────────────────────────────────────────────────────────
# ユーティリティ
# ─────────────────────────────────────────────────────────────

def _unwrap_cause(exc: BaseException) -> BaseException:
    """
    ChildWorkflowError / ActivityError でラップされた根本原因を取り出す。
    `__cause__` チェーンを辿って最奥の例外を返す。
    """
    current = exc
    for _ in range(10):   # 無限ループ防止
        if current.__cause__ is None:
            return current
        current = current.__cause__
    return current


def _build_cause_chain(exc: BaseException) -> list[str]:
    """
    例外の原因チェーンを文字列リストにして返す（開発環境デバッグ用）。
    ["ChildWorkflowError: ...", "ActivityError: ...", "RuntimeError: ..."] の形式。
    """
    chain: list[str] = []
    current: BaseException | None = exc
    for _ in range(10):
        if current is None:
            break
        chain.append(f"{type(current).__name__}: {current}")
        current = current.__cause__
    return chain
