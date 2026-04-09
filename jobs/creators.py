"""
VideoJob を作成するクリエイター。

設計:
  JobCreatorProtocol         ─ インターフェース（Protocol）
  VideoJobCreator            ─ VideoJob（DB）を作成する具体的な実装
  VideoAiConfigNotFoundError ─ credential / model が見つからない場合の例外
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


# ─────────────────────────────────────────────────────────────
# 例外
# ─────────────────────────────────────────────────────────────

class VideoAiConfigNotFoundError(Exception):
    """指定した credential / model が見つからない、または無効な場合。"""


# ─────────────────────────────────────────────────────────────
# インターフェース（Protocol）
# ─────────────────────────────────────────────────────────────

class JobCreatorProtocol(Protocol):
    def create(
        self,
        user,
        channel_id: int,
        credential_id: int,
        model_id: int,
        script: str,
        image_ids: list[int],
        audio_ids: list[int],
        publish_mode: str,
        video_length: int,
        image_descriptions: dict[int, str],
        audio_descriptions: dict[int, str],
    ) -> Any:
        ...


# ─────────────────────────────────────────────────────────────
# 具体的なクリエイター実装
# ─────────────────────────────────────────────────────────────

class VideoJobCreator:
    """
    VideoJob / VideoJobAsset / VideoJobEvent を DB に作成するクリエイター。

    Raises:
        VideoAiConfigNotFoundError: credential_id / model_id が無効な場合
        YoutubeChannel.DoesNotExist: channel_id が不正な場合
    """

    def create(
        self,
        user,
        channel_id: int,
        credential_id: int,
        model_id: int,
        script: str,
        image_ids: list[int] | None = None,
        audio_ids: list[int] | None = None,
        publish_mode: str = 'private',
        video_length: int = 5,
        image_descriptions: dict[int, str] | None = None,
        audio_descriptions: dict[int, str] | None = None,
    ) -> VideoJob:
        image_ids = image_ids or []
        audio_ids = audio_ids or []
        image_descriptions = image_descriptions or {}
        audio_descriptions = audio_descriptions or {}

        credential, model = self._resolve_credential_and_model(user, credential_id, model_id)
        channel = (
            YoutubeChannel.objects
            .select_related('user_google_account')
            .get(pk=channel_id, user_google_account__user=user)
        )

        with transaction.atomic():
            prompt = Prompt.objects.create(user=user, prompt_text=script)

            job = VideoJob.objects.create(
                user=user,
                status=JobStatus.QUEUED,
                request_type=RequestType.GENERATE_AND_PUBLISH,
                prompt=prompt,
                credential_id=credential.id,
                model_id=model.id,
                google_account=channel.user_google_account,
                youtube_channel=channel,
                publish_mode=publish_mode,
                video_length=video_length,
            )

            VideoJobAsset.objects.bulk_create([
                VideoJobAsset(
                    job=job,
                    asset_id=img_id,
                    asset_role=AssetRole.MAIN_IMAGE,
                    description=image_descriptions.get(img_id, ''),
                )
                for img_id in image_ids
            ])

            VideoJobAsset.objects.bulk_create([
                VideoJobAsset(
                    job=job,
                    asset_id=aud_id,
                    asset_role=AssetRole.BGM,
                    description=audio_descriptions.get(aud_id, ''),
                )
                for aud_id in audio_ids
            ])

            VideoJobEvent.objects.create(
                job=job,
                event_type=EventType.JOB_CREATED,
                message=f"Job created  credential={credential.id}  model={model.model_name}",
                payload_json={
                    'credential_id': credential.id,
                    'model_id':      model.id,
                    'model_name':    model.model_name,
                    'image_ids':     image_ids,
                    'audio_ids':     audio_ids,
                },
            )

        return job

    def _resolve_credential_and_model(self, user, credential_id: int, model_id: int):
        from video_ai.models import UserVideoAiCredential, VideoAiModel

        try:
            credential = (
                UserVideoAiCredential.objects
                .select_related('provider')
                .get(id=credential_id, user=user, is_active=True)
            )
        except UserVideoAiCredential.DoesNotExist:
            raise VideoAiConfigNotFoundError(
                f"APIキーが見つかりません。プロバイダーの設定を確認してください。（credential_id={credential_id}）"
            )

        try:
            model = VideoAiModel.objects.get(
                id=model_id,
                provider=credential.provider,
                is_active=True,
            )
        except VideoAiModel.DoesNotExist:
            raise VideoAiConfigNotFoundError(
                f"モデルが見つかりません。管理者にお問い合わせください。（model_id={model_id}）"
            )

        return credential, model
