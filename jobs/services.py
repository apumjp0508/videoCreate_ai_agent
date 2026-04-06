"""
VideoJob の作成・Temporal Workflow 起動を担うサービス層。

View はここだけを呼ぶ。DB 操作・Temporal 呼び出しのロジックはここに集約する。

公開 API:
  create_video_job(...)        → DB に Job / Asset / Event を作成して VideoJob を返す
  start_workflow_for_job(job)  → Temporal Workflow を起動して job に workflow_id を書き戻す
  VideoAiConfigNotFoundError   → AI 設定が見つからない場合の例外
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from django.conf import settings
from django.db import transaction

from google_auth.models import OauthToken, YoutubeChannel
from jobs.models import (
    AssetRole,
    EventType,
    JobStatus,
    RequestType,
    VideoJob,
    VideoJobAsset,
    VideoJobEvent,
)
from temporal.client import get_temporal_client
from temporal.pipeline_types import PipelineInput
from temporal.workflows.pipeline.video_pipeline_workflow import VideoPipelineWorkflow
from video_ai.models import UserVideoAiConfig


# ─────────────────────────────────────────────────────────────
# 例外
# ─────────────────────────────────────────────────────────────

class VideoAiConfigNotFoundError(Exception):
    """指定した provider_key に対応する有効な UserVideoAiConfig が存在しない場合。"""


class WorkflowStartError(Exception):
    """Temporal Workflow の起動に失敗した場合。"""


# ─────────────────────────────────────────────────────────────
# 内部ヘルパー
# ─────────────────────────────────────────────────────────────

def _resolve_video_ai_config(user, provider_key: str) -> UserVideoAiConfig:
    """
    provider_key からユーザーのデフォルト UserVideoAiConfig を解決する。

    Raises:
        VideoAiConfigNotFoundError: 対応する設定が見つからない場合
    """
    config = (
        UserVideoAiConfig.objects
        .filter(
            user=user,
            provider__provider_key=provider_key,
            is_default=True,
            is_active=True,
        )
        .select_related('provider')
        .first()
    )
    if config is None:
        raise VideoAiConfigNotFoundError(
            f"AI設定が見つかりません。プロバイダー「{provider_key}」の設定を登録してください。"
        )
    return config


def _get_oauth_record_id(channel: YoutubeChannel) -> int:
    """チャンネルに紐づく OauthToken の id を返す。未取得なら 0。"""
    try:
        return channel.user_google_account.oauth_token.id
    except OauthToken.DoesNotExist:
        return 0


# ─────────────────────────────────────────────────────────────
# 公開 API
# ─────────────────────────────────────────────────────────────

def create_video_job(
    user,
    channel_id: int,
    provider_key: str,
    script: str,
    image_id: int | None,
    audio_id: int | None,
) -> VideoJob:
    """
    VideoJob / VideoJobAsset / VideoJobEvent を DB に作成して VideoJob を返す。

    DB 操作はすべてトランザクション1本で行う。
    Temporal の起動はここでは行わない（start_workflow_for_job を別途呼ぶ）。

    Args:
        user:         ログイン中ユーザー
        channel_id:   YoutubeChannel の PK
        provider_key: "runway" | "pika" | "kling" など
        script:       コンテンツ選択画面で入力したスクリプト
        image_id:     選択した GeneratedImage の PK（なければ None）
        audio_id:     選択した GeneratedAudio の PK（なければ None）

    Raises:
        VideoAiConfigNotFoundError: provider_key に対応する設定が存在しない場合
        YoutubeChannel.DoesNotExist: channel_id が不正な場合
    """
    config = _resolve_video_ai_config(user, provider_key)
    channel = (
        YoutubeChannel.objects
        .select_related('user_google_account')
        .get(pk=channel_id, user_google_account__user=user)
    )

    with transaction.atomic():
        job = VideoJob.objects.create(
            user=user,
            status=JobStatus.QUEUED,
            request_type=RequestType.GENERATE_AND_PUBLISH,
            prompt_text=script,
            video_ai_config_id=config.id,
            google_account=channel.user_google_account,
            youtube_channel=channel,
        )

        if image_id:
            VideoJobAsset.objects.create(
                job=job,
                asset_id=image_id,
                asset_role=AssetRole.MAIN_IMAGE,
            )

        if audio_id:
            VideoJobAsset.objects.create(
                job=job,
                asset_id=audio_id,
                asset_role=AssetRole.BGM,
            )

        VideoJobEvent.objects.create(
            job=job,
            event_type=EventType.JOB_CREATED,
            message=f"Job created  provider={provider_key}  config_id={config.id}",
            payload_json={
                'provider_key':  provider_key,
                'config_id':     config.id,
                'image_id':      image_id,
                'audio_id':      audio_id,
            },
        )

    return job


def start_workflow_for_job(job: VideoJob) -> None:
    """
    Temporal Workflow を起動して job に workflow_id / run_id を書き戻す。

    DB トランザクションの外から呼ぶこと。
    起動に失敗した場合は job.status を failed に更新して WorkflowStartError を送出する。

    Raises:
        WorkflowStartError: Temporal への接続・起動に失敗した場合
    """
    try:
        asyncio.run(_start_workflow_async(job))
    except Exception as exc:
        # Workflow 起動失敗 → job を failed に更新してから re-raise
        job.status = JobStatus.FAILED
        job.error_code = 'WORKFLOW_START_ERROR'
        job.error_message = str(exc)
        job.save(update_fields=['status', 'error_code', 'error_message', 'updated_at'])

        VideoJobEvent.objects.create(
            job=job,
            event_type=EventType.JOB_FAILED,
            message=f"Workflow start failed: {exc}",
            payload_json={'error': str(exc)},
        )
        raise WorkflowStartError(str(exc)) from exc


async def _start_workflow_async(job: VideoJob) -> None:
    """Temporal Client から Workflow を start して job に結果を書き戻す（非同期）。"""
    channel = job.youtube_channel
    oauth_record_id = _get_oauth_record_id(channel)

    # 選択された asset_id を role ごとに収集する
    assets = job.assets.all()
    image_ids = [a.asset_id for a in assets if a.asset_role == AssetRole.MAIN_IMAGE]
    audio_ids = [a.asset_id for a in assets if a.asset_role == AssetRole.BGM]

    pipeline_input = PipelineInput(
        job_id=str(job.id),
        request_id=str(uuid.uuid4()),
        user_id=job.user_id,
        video_ai_config_id=job.video_ai_config_id or 0,
        # TODO: prompt テーブルが出来たら job.id ではなく実際の prompt_id に差し替える
        prompt_id=job.id,
        image_ids=image_ids,
        audio_ids=audio_ids,
        oauth_record_id=oauth_record_id,
        youtube_channel_id=channel.youtube_channel_id,
        publish_mode='private',
    )

    client = await get_temporal_client()
    handle = await client.start_workflow(
        VideoPipelineWorkflow.run,
        pipeline_input,
        id=str(job.id),
        task_queue=settings.TEMPORAL_TASK_QUEUE,
    )

    # Workflow 起動成功 → job を更新
    job.temporal_workflow_id = handle.id
    job.temporal_run_id = handle.first_execution_run_id
    job.status = JobStatus.GENERATING
    job.started_at = datetime.now(timezone.utc)
    job.save(update_fields=[
        'temporal_workflow_id', 'temporal_run_id',
        'status', 'started_at', 'updated_at',
    ])

    VideoJobEvent.objects.create(
        job=job,
        event_type=EventType.WORKFLOW_STARTED,
        message=f"Workflow started  id={handle.id}",
        payload_json={
            'workflow_id': handle.id,
            'run_id': handle.first_execution_run_id,
        },
    )
