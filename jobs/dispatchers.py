"""
Job を Workflow エンジンへ送信するディスパッチャー。

設計:
  WorkflowDispatcherProtocol  ─ インターフェース（Protocol）
  TemporalWorkflowDispatcher  ─ Temporal へ送信する具体的な実装
  WorkflowStartError          ─ 送信失敗時の例外

Job の作成（creators.py）・Input の組み立て（builders.py）とは独立した責務。
Workflow エンジンが Temporal 以外になっても、ここだけ差し替えればよい。

例:
  # 将来の別 Workflow エンジンに差し替える場合
  dispatcher = SomeOtherDispatcher()
  start_workflow_for_job(job, dispatcher=dispatcher)
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Protocol

from django.conf import settings

from jobs.builders import PipelineInputBuilderProtocol
from jobs.models import EventType, JobStatus, VideoJob, VideoJobEvent
from temporal.client import get_temporal_client
from temporal.workflows.pipeline.video_pipeline_workflow import VideoPipelineWorkflow


# ─────────────────────────────────────────────────────────────
# 例外
# ─────────────────────────────────────────────────────────────

class WorkflowStartError(Exception):
    """Workflow エンジンへの送信に失敗した場合。"""


# ─────────────────────────────────────────────────────────────
# インターフェース（Protocol）
# ─────────────────────────────────────────────────────────────

class WorkflowDispatcherProtocol(Protocol):
    """
    Job を Workflow エンジンへ送信するインターフェース。

    Workflow エンジンの種類（Temporal / その他）が変わっても
    呼び出し側（services.py）は変更不要。
    """

    def dispatch(
        self,
        job: VideoJob,
        builder: PipelineInputBuilderProtocol,
    ) -> None:
        """
        builder で Pipeline Input を組み立てて Workflow エンジンへ送信する。

        送信成功後は job.temporal_workflow_id / run_id / status を更新する。

        Raises:
            WorkflowStartError: 送信に失敗した場合
        """
        ...


# ─────────────────────────────────────────────────────────────
# 具体的なディスパッチャー実装
# ─────────────────────────────────────────────────────────────

class TemporalWorkflowDispatcher:
    """
    Temporal Workflow へ job を送信するディスパッチャー。

    builder.build(job) で Pipeline Input を組み立てたあと、
    Temporal Client を通じて VideoPipelineWorkflow を起動する。
    起動成功後は job のステータス・Workflow ID を DB に書き戻す。

    Raises:
        WorkflowStartError: Temporal への接続・起動に失敗した場合
    """

    def dispatch(
        self,
        job: VideoJob,
        builder: PipelineInputBuilderProtocol,
    ) -> None:
        try:
            # DB クエリを含む build() は同期コンテキストで先に実行する
            pipeline_input = builder.build(job)
            handle_id, run_id = asyncio.run(self._start_workflow_async(pipeline_input, job.id))
        except WorkflowStartError:
            raise
        except Exception as exc:
            self._mark_failed(job, exc)
            raise WorkflowStartError(str(exc)) from exc

        # 起動成功 → DB 書き込みも同期コンテキストで行う
        job.temporal_workflow_id = handle_id
        job.temporal_run_id = run_id
        job.status = JobStatus.GENERATING
        job.started_at = datetime.now(timezone.utc)
        job.save(update_fields=[
            'temporal_workflow_id', 'temporal_run_id',
            'status', 'started_at', 'updated_at',
        ])

        VideoJobEvent.objects.create(
            job=job,
            event_type=EventType.WORKFLOW_STARTED,
            message=f"Workflow started  id={handle_id}",
            payload_json={
                'workflow_id': handle_id,
                'run_id': run_id,
            },
        )

    async def _start_workflow_async(self, pipeline_input, job_id) -> tuple[str, str]:
        """Temporal Workflow を起動して (workflow_id, run_id) を返す（非同期）。"""
        client = await get_temporal_client()
        handle = await client.start_workflow(
            VideoPipelineWorkflow.run,
            pipeline_input,
            id=str(job_id),
            task_queue=settings.TEMPORAL_TASK_QUEUE,
        )
        return handle.id, handle.first_execution_run_id

    def _mark_failed(self, job: VideoJob, exc: Exception) -> None:
        """送信失敗時に job を failed 状態に更新してイベントを記録する。"""
        job.status = JobStatus.FAILED
        job.error_code = 'WORKFLOW_START_ERROR'
        job.error_message = str(exc)
        job.save(update_fields=['status', 'error_code', 'error_message', 'updated_at'])

        VideoJobEvent.objects.create(
            job=job,
            event_type=EventType.JOB_FAILED,
            message=f"Workflow dispatch failed: {exc}",
            payload_json={'error': str(exc)},
        )
