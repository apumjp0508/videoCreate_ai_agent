"""
Django → Temporal の橋渡し層。
View/API から呼び出して Workflow を起動する。
"""
import asyncio
import uuid

from temporalio.client import WorkflowFailureError

from temporal.client import get_temporal_client
from temporal.models import WorkflowAdminPermission
from temporal.pipeline_types import PipelineInput, PipelineOutput
from temporal.workflows.pipeline.video_pipeline_workflow import VideoPipelineWorkflow


def has_workflow_permission(user) -> bool:
    """admin_workflow テーブルで権限を持つユーザーか確認する。"""
    return WorkflowAdminPermission.objects.filter(
        user=user,
        is_active=True,
    ).exists()


def _new_job_id() -> str:
    return str(uuid.uuid4())


async def _start_pipeline_async(input: PipelineInput) -> PipelineOutput:
    client = await get_temporal_client()
    result: PipelineOutput = await client.execute_workflow(
        VideoPipelineWorkflow.run,
        input,
        id=input.job_id,
        task_queue="video-job-queue",
    )
    return result


def start_video_pipeline(input: PipelineInput) -> PipelineOutput:
    """
    VideoPipelineWorkflow を起動して完了まで待機する同期ラッパー。
    Django の同期 view から直接呼べる。
    """
    try:
        return asyncio.run(_start_pipeline_async(input))
    except WorkflowFailureError as exc:
        raise RuntimeError(f"Workflow failed: {exc}") from exc
