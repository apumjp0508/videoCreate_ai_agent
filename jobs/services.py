"""
VideoJob の作成・Temporal Workflow 起動を担うサービス層。

View はここだけを呼ぶ。各機能の詳細は専用モジュールに委譲する。

公開 API:
  create_video_job(...)                → creator が Job を DB に保存して返す
  start_workflow_for_job(job, ...)     → builder が Input を組み立て、dispatcher が Temporal へ送信する

インターフェースと具体実装（差し替えポイント）:
  creators.py:
    JobCreatorProtocol         → Job 作成のインターフェース
    VideoJobCreator            → VideoJob を作成する具体実装（デフォルト）
    VideoAiConfigNotFoundError → AI 設定が見つからない場合の例外

  builders.py:
    PipelineInputBuilderProtocol → Pipeline Input 組み立てのインターフェース
    VideoPipelineInputBuilder    → VideoPipelineWorkflow 用の具体実装（デフォルト）
    PipelineInputBuildError      → 組み立て失敗時の例外

  dispatchers.py:
    WorkflowDispatcherProtocol → Workflow エンジンへの送信インターフェース
    TemporalWorkflowDispatcher → Temporal へ送信する具体実装（デフォルト）
    WorkflowStartError         → 送信失敗時の例外

呼び出し順:
  1. create_video_job(...)        → creator が Job を DB に保存
  2. start_workflow_for_job(job)  → builder が Input を組み立て → dispatcher が Temporal へ送信
     ※ 各引数を省略するとデフォルト実装が使われる
"""
from __future__ import annotations

from jobs.builders import (
    PipelineInputBuilderProtocol,
    VideoPipelineInputBuilder,
)
from jobs.creators import (
    JobCreatorProtocol,
    VideoAiConfigNotFoundError,
    VideoJobCreator,
)
from jobs.dispatchers import (
    TemporalWorkflowDispatcher,
    WorkflowDispatcherProtocol,
    WorkflowStartError,
)
from jobs.models import VideoJob


# ─────────────────────────────────────────────────────────────
# 公開 API
# ─────────────────────────────────────────────────────────────

def create_video_job(
    user,
    channel_id: int,
    credential_id: int,
    model_id: int,
    script: str,
    image_ids: list[int] | None = None,
    audio_ids: list[int] | None = None,
    publish_mode: str = 'private',
    image_descriptions: dict[int, str] | None = None,
    audio_descriptions: dict[int, str] | None = None,
    creator: JobCreatorProtocol | None = None,
) -> VideoJob:
    """
    creator を通じて VideoJob を DB に作成して返す。

    Args:
        creator: Job 作成インターフェースの実装（省略時は VideoJobCreator）

    Raises:
        VideoAiConfigNotFoundError: credential / model が無効な場合
        YoutubeChannel.DoesNotExist: channel_id が不正な場合
    """
    if creator is None:
        creator = VideoJobCreator()

    return creator.create(
        user=user,
        channel_id=channel_id,
        credential_id=credential_id,
        model_id=model_id,
        script=script,
        image_ids=image_ids or [],
        audio_ids=audio_ids or [],
        publish_mode=publish_mode,
        image_descriptions=image_descriptions or {},
        audio_descriptions=audio_descriptions or {},
    )


def start_workflow_for_job(
    job: VideoJob,
    builder: PipelineInputBuilderProtocol | None = None,
    dispatcher: WorkflowDispatcherProtocol | None = None,
) -> None:
    """
    builder で Pipeline Input を組み立てて dispatcher が Workflow エンジンへ送信する。

    DB トランザクションの外から呼ぶこと。

    Args:
        job:        起動対象の VideoJob
        builder:    Pipeline Input を組み立てるビルダー（省略時は VideoPipelineInputBuilder）
        dispatcher: Workflow エンジンへの送信実装（省略時は TemporalWorkflowDispatcher）

    Raises:
        WorkflowStartError: 送信に失敗した場合
    """
    if builder is None:
        builder = VideoPipelineInputBuilder()
    if dispatcher is None:
        dispatcher = TemporalWorkflowDispatcher()

    dispatcher.dispatch(job, builder)
