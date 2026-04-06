"""
Django → Temporal の橋渡し層。
View/API から呼び出して Workflow を起動する。
"""
import asyncio
import uuid

from temporalio.client import WorkflowFailureError

from temporal.client import get_temporal_client
from temporal.models import WorkflowAdminPermission
from temporal.types import VideoJobInput, VideoJobOutput
from temporal.workflows.video_job_workflow import VideoJobWorkflow


def has_workflow_permission(user) -> bool:
    """admin_workflow テーブルで権限を持つユーザーか確認する。"""
    return WorkflowAdminPermission.objects.filter(
        user=user,
        is_active=True,
    ).exists()


def _new_job_id() -> str:
    return str(uuid.uuid4())


async def _start_video_job_async(input: VideoJobInput) -> VideoJobOutput:
    client = await get_temporal_client()
    result: VideoJobOutput = await client.execute_workflow(
        VideoJobWorkflow.run,
        input,
        id=f"video-job-{input.job_id}",
        task_queue="video-job-queue",
    )
    return result


def start_video_job(input: VideoJobInput) -> VideoJobOutput:
    """
    Workflow を起動して完了まで待機する同期ラッパー。
    Django の同期 view から直接呼べる。
    """
    try:
        return asyncio.run(_start_video_job_async(input))
    except WorkflowFailureError as exc:
        raise RuntimeError(f"Workflow failed: {exc}") from exc
