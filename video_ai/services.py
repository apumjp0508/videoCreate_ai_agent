"""
Django → Temporal の橋渡し層。
View/API から呼び出して Workflow を起動する。

使い方 (同期コンテキスト = 通常の Django view):
    from video_ai.services import start_video_job

    result = start_video_job(job_id="abc123", prompt="猫の動画を作って")
    # result.youtube_video_id に結果が入る (Workflow 完了まで待機)

非同期が不要な場合は asyncio.run() でラップしているので
普通の Django view からそのまま呼べる。
"""
import asyncio
import uuid

from temporalio.client import WorkflowFailureError

from temporal.client import get_temporal_client
from temporal.workflows.video_job_workflow import VideoJobParams, VideoJobResult, VideoJobWorkflow


def _new_job_id() -> str:
    return str(uuid.uuid4())


async def _start_video_job_async(job_id: str, prompt: str) -> VideoJobResult:
    client = await get_temporal_client()
    result: VideoJobResult = await client.execute_workflow(
        VideoJobWorkflow.run,
        VideoJobParams(job_id=job_id, prompt=prompt),
        id=f"video-job-{job_id}",
        task_queue="video-job-queue",
    )
    return result


def start_video_job(prompt: str, job_id: str | None = None) -> VideoJobResult:
    """
    Workflow を起動して完了まで待機する同期ラッパー。

    - job_id を省略すると UUID が自動生成される。
    - Django の同期 view から直接呼べる。
    """
    if job_id is None:
        job_id = _new_job_id()
    try:
        return asyncio.run(_start_video_job_async(job_id=job_id, prompt=prompt))
    except WorkflowFailureError as exc:
        raise RuntimeError(f"Workflow failed: {exc}") from exc
