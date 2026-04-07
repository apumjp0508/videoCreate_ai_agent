"""
VideoJob を作成するクリエイター。

設計:
  JobCreatorProtocol         ─ インターフェース（Protocol）
  VideoJobCreator            ─ VideoJob（DB）を作成する具体的な実装
  VideoAiConfigNotFoundError ─ AI 設定が見つからない場合の例外

クリエイターを差し替えることで、将来の別 Job 形態にも対応できる。

例:
  # 将来の別 Job 形態に差し替える場合
  creator = SomeOtherJobCreator()
  create_video_job(..., creator=creator)
"""
from __future__ import annotations

from typing import Any, Protocol

from django.db import transaction

from google_auth.models import YoutubeChannel
from jobs.models import (
    AssetRole,
    EventType,
    JobStatus,
    Prompt,
    RequestType,
    VideoJob,
    VideoJobAsset,
    VideoJobEvent,
)
from video_ai.models import UserVideoAiConfig


# ─────────────────────────────────────────────────────────────
# 例外
# ─────────────────────────────────────────────────────────────

class VideoAiConfigNotFoundError(Exception):
    """指定した provider_key に対応する有効な UserVideoAiConfig が存在しない場合。"""


# ─────────────────────────────────────────────────────────────
# インターフェース（Protocol）
# ─────────────────────────────────────────────────────────────

class JobCreatorProtocol(Protocol):
    """
    Job を作成するインターフェース。

    Job の形が変わっても呼び出し側（services.py）は変更不要。
    Workflow の種類や Job の種類が増えたときに実装を差し替える。
    """

    def create(
        self,
        user,
        channel_id: int,
        provider_key: str,
        script: str,
        image_id: int | None,
        audio_id: int | None,
        publish_mode: str,
    ) -> Any:
        """
        Job を DB に作成して返す。

        Raises:
            VideoAiConfigNotFoundError: provider_key に対応する設定が存在しない場合
        """
        ...


# ─────────────────────────────────────────────────────────────
# 具体的なクリエイター実装
# ─────────────────────────────────────────────────────────────

class VideoJobCreator:
    """
    VideoJob / VideoJobAsset / VideoJobEvent を DB に作成するクリエイター。

    DB 操作はすべてトランザクション1本で行う。
    Temporal の起動はここでは行わない（start_workflow_for_job を別途呼ぶ）。

    Raises:
        VideoAiConfigNotFoundError: provider_key に対応する設定が存在しない場合
        YoutubeChannel.DoesNotExist: channel_id が不正な場合
    """

    def create(
        self,
        user,
        channel_id: int,
        provider_key: str,
        script: str,
        image_id: int | None,
        audio_id: int | None,
        publish_mode: str = 'private',
    ) -> VideoJob:
        config = self._resolve_video_ai_config(user, provider_key)
        channel = (
            YoutubeChannel.objects
            .select_related('user_google_account')
            .get(pk=channel_id, user_google_account__user=user)
        )

        with transaction.atomic():
            # プロンプトを先に保存して prompt_id を確定させる
            prompt = Prompt.objects.create(user=user, prompt_text=script)

            job = VideoJob.objects.create(
                user=user,
                status=JobStatus.QUEUED,
                request_type=RequestType.GENERATE_AND_PUBLISH,
                prompt=prompt,
                video_ai_config_id=config.id,
                google_account=channel.user_google_account,
                youtube_channel=channel,
                publish_mode=publish_mode,
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

    def _resolve_video_ai_config(self, user, provider_key: str) -> UserVideoAiConfig:
        """provider_key からユーザーのデフォルト UserVideoAiConfig を解決する。"""
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
