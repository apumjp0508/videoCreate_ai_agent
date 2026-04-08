"""
YoutubePublish Activity の Django / YouTube API 実装。

実装済み Activity:
  DB 操作:
    - fetch_youtube_account    Django ORM（YoutubeChannel）
    - fetch_oauth_token        Django ORM（OauthToken + Fernet 復号）
    - fetch_publish_settings   VideoJob の publish_mode + AI 生成オーバーライド
    - save_publish_result      VideoJob を COMPLETED に更新・YouTube フィールド保存

  純粋ロジック:
    - build_upload_request     YouTube Data API v3 のリクエスト構造体を組み立て

  Google / YouTube API（YoutubeApiServiceProtocol に委譲）:
    - refresh_access_token     Google OAuth トークンリフレッシュ + DB 更新
    - upload_video_to_youtube  YouTube Resumable Upload
    - set_thumbnail            YouTube Thumbnails.set
    - apply_publish_settings   YouTube Videos.update（privacy）

設計方針:
  - YoutubeApiServiceProtocol を DI することで YouTube API の実装を差し替え可能にする
  - DB 操作は sync_to_async でスレッド実行
  - API キーは Temporal ヒストリに露出させない

差し替え方:
  worker_pipeline.py で以下のように _service を上書きする:

    from temporal.activities.youtube_publish import dummy as yt_dummy
    from temporal.activities.youtube_publish.django_service import DjangoYoutubePublishService
    from temporal.activities.youtube_publish.youtube_api_service import YoutubeDataApiService
    yt_dummy._service = DjangoYoutubePublishService(youtube_api=YoutubeDataApiService())
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from asgiref.sync import sync_to_async
from django.conf import settings

from temporal.activities.youtube_publish.dummy import DummyYoutubePublishService
from temporal.activities.youtube_publish.interfaces import (
    ApplyPublishSettingsInput,
    ApplyPublishSettingsOutput,
    BuildUploadRequestInput,
    BuildUploadRequestOutput,
    FetchOAuthTokenInput,
    FetchOAuthTokenOutput,
    FetchPublishSettingsInput,
    FetchPublishSettingsOutput,
    FetchYoutubeAccountInput,
    FetchYoutubeAccountOutput,
    RefreshAccessTokenInput,
    RefreshAccessTokenOutput,
    SavePublishResultInput,
    SavePublishResultOutput,
    SetThumbnailInput,
    SetThumbnailOutput,
    UploadVideoToYoutubeInput,
    UploadVideoToYoutubeOutput,
)
from temporal.activities.youtube_publish.youtube_api_service import (
    YoutubeApiServiceProtocol,
    YoutubeDataApiService,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# ドメイン例外
# ─────────────────────────────────────────────────────────────

class YoutubeAccountNotFoundError(Exception):
    """指定された YouTubeChannel が DB に存在しない場合。"""


class OAuthTokenNotFoundError(Exception):
    """指定された OauthToken が DB に存在しない場合。"""


# ─────────────────────────────────────────────────────────────
# サービス実装
# ─────────────────────────────────────────────────────────────

class DjangoYoutubePublishService(DummyYoutubePublishService):
    """
    YoutubePublishServiceProtocol の Django / YouTube API 実装。

    Args:
        youtube_api: YouTube API 操作を担うサービス。
                     None の場合は YoutubeDataApiService を使う。
    """

    def __init__(self, youtube_api: YoutubeApiServiceProtocol | None = None) -> None:
        self._youtube_api = youtube_api or YoutubeDataApiService()

    # ── fetch_youtube_account（DB）──────────────────────────────

    async def fetch_youtube_account(
        self, input: FetchYoutubeAccountInput
    ) -> FetchYoutubeAccountOutput:
        logger.info(
            "fetch_youtube_account  job_id=%s  channel=%s",
            input.job_id, input.youtube_channel_id,
        )
        return await sync_to_async(self._fetch_youtube_account_sync)(input)

    def _fetch_youtube_account_sync(
        self, input: FetchYoutubeAccountInput
    ) -> FetchYoutubeAccountOutput:
        from google_auth.models import YoutubeChannel

        try:
            channel = YoutubeChannel.objects.select_related(
                "user_google_account"
            ).get(
                youtube_channel_id=input.youtube_channel_id,
                user_google_account__user_id=input.user_id,
                is_active=True,
            )
        except YoutubeChannel.DoesNotExist:
            raise YoutubeAccountNotFoundError(
                f"YoutubeChannel not found: channel_id={input.youtube_channel_id} "
                f"user_id={input.user_id}"
            )

        return FetchYoutubeAccountOutput(
            channel_id=channel.youtube_channel_id,
            channel_title=channel.title,
            channel_metadata={
                "handle": channel.handle,
                "thumbnail_url": channel.thumbnail_url,
                "is_default": channel.is_default,
            },
        )

    # ── fetch_oauth_token（DB + 復号）────────────────────────────

    async def fetch_oauth_token(
        self, input: FetchOAuthTokenInput
    ) -> FetchOAuthTokenOutput:
        logger.info(
            "fetch_oauth_token  job_id=%s  oauth_record_id=%s",
            input.job_id, input.oauth_record_id,
        )
        return await sync_to_async(self._fetch_oauth_token_sync)(input)

    def _fetch_oauth_token_sync(
        self, input: FetchOAuthTokenInput
    ) -> FetchOAuthTokenOutput:
        from google_auth.models import OauthToken
        from google_auth.services import decrypt_token

        try:
            token = OauthToken.objects.get(id=input.oauth_record_id)
        except OauthToken.DoesNotExist:
            raise OAuthTokenNotFoundError(
                f"OauthToken not found: id={input.oauth_record_id}"
            )

        access_token = decrypt_token(token.access_token_encrypted)
        refresh_token = decrypt_token(token.refresh_token_encrypted) if token.refresh_token_encrypted else ""

        is_expired = (
            token.expires_at is not None
            and token.expires_at <= datetime.now(tz=timezone.utc)
        )
        expires_at_str = (
            token.expires_at.isoformat() if token.expires_at else ""
        )

        return FetchOAuthTokenOutput(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at_str,
            is_expired=is_expired,
        )

    # ── refresh_access_token（Google API + DB 更新）──────────────

    async def refresh_access_token(
        self, input: RefreshAccessTokenInput
    ) -> RefreshAccessTokenOutput:
        logger.info("refresh_access_token  job_id=%s", input.job_id)

        result = await self._youtube_api.call_refresh_token(
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            refresh_token=input.refresh_token,
        )

        new_access_token = result["access_token"]
        expires_in_sec = result.get("expires_in", 3600)

        # DB のトークンを更新
        await sync_to_async(self._update_oauth_token_sync)(
            oauth_record_id=input.oauth_record_id,
            new_access_token=new_access_token,
            expires_in_sec=expires_in_sec,
        )

        from datetime import timedelta
        new_expires_at = (
            datetime.now(tz=timezone.utc) + timedelta(seconds=expires_in_sec)
        ).isoformat()

        return RefreshAccessTokenOutput(
            access_token=new_access_token,
            new_expires_at=new_expires_at,
        )

    def _update_oauth_token_sync(
        self,
        oauth_record_id: int,
        new_access_token: str,
        expires_in_sec: int,
    ) -> None:
        from datetime import timedelta
        from google_auth.models import OauthToken
        from google_auth.services import encrypt_token

        new_expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=expires_in_sec)
        OauthToken.objects.filter(id=oauth_record_id).update(
            access_token_encrypted=encrypt_token(new_access_token),
            expires_at=new_expires_at,
            last_refreshed_at=datetime.now(tz=timezone.utc),
        )

    # ── fetch_publish_settings（DB + AI生成オーバーライド）────────

    async def fetch_publish_settings(
        self, input: FetchPublishSettingsInput
    ) -> FetchPublishSettingsOutput:
        logger.info(
            "fetch_publish_settings  job_id=%s  title_override=%s",
            input.job_id, bool(input.title_override),
        )
        return await sync_to_async(self._fetch_publish_settings_sync)(input)

    def _fetch_publish_settings_sync(
        self, input: FetchPublishSettingsInput
    ) -> FetchPublishSettingsOutput:
        from jobs.models import VideoJob

        job = VideoJob.objects.select_related("prompt").get(id=int(input.job_id))

        # AI 生成メタ情報を優先。未提供時は job / prompt から生成する
        title = (
            input.title_override
            or self._default_title(job)
        )
        description = (
            input.description_override
            or self._default_description(job)
        )
        tags = input.tags_override or []
        publish_mode = input.publish_mode_override or job.publish_mode or "private"

        return FetchPublishSettingsOutput(
            title=title,
            description=description,
            tags=tags,
            category_id="22",   # People & Blogs（将来: DB から取得）
            publish_mode=publish_mode,
        )

    @staticmethod
    def _default_title(job) -> str:
        if job.prompt and job.prompt.prompt_text:
            preview = job.prompt.prompt_text[:50].replace("\n", " ")
            return f"AI動画: {preview}"
        return f"AI生成動画 #{job.id}"

    @staticmethod
    def _default_description(job) -> str:
        if job.prompt and job.prompt.prompt_text:
            return f"このAI動画は次のプロンプトをもとに生成されました。\n\n{job.prompt.prompt_text}"
        return "AI によって自動生成された動画です。"

    # ── build_upload_request（純粋ロジック）──────────────────────

    async def build_upload_request(
        self, input: BuildUploadRequestInput
    ) -> BuildUploadRequestOutput:
        """YouTube Data API v3 の videos.insert 用リクエスト構造体を組み立てる。"""
        logger.info("build_upload_request  job_id=%s  title=%s", input.job_id, input.title)
        metadata = {
            "snippet": {
                "title": input.title,
                "description": input.description,
                "tags": input.tags,
                "categoryId": input.category_id,
                "channelId": input.channel_id,
            },
            "status": {
                "privacyStatus": input.publish_mode,
                "selfDeclaredMadeForKids": False,
            },
        }
        return BuildUploadRequestOutput(
            upload_request=metadata,
            video_url=input.video_url,
        )

    # ── upload_video_to_youtube（YouTube API）────────────────────

    async def upload_video_to_youtube(
        self, input: UploadVideoToYoutubeInput
    ) -> UploadVideoToYoutubeOutput:
        logger.info("upload_video_to_youtube  job_id=%s", input.job_id)

        youtube_video_id = await self._youtube_api.upload_video(
            access_token=input.access_token,
            metadata=input.upload_request,
            video_url=input.video_url,
        )
        youtube_video_url = f"https://www.youtube.com/watch?v={youtube_video_id}"
        logger.info(
            "upload_video_to_youtube done  job_id=%s  yt_id=%s",
            input.job_id, youtube_video_id,
        )

        # YouTube アップロード完了イベントを記録
        await sync_to_async(self._record_upload_completed)(
            input.job_id, youtube_video_id, youtube_video_url
        )

        return UploadVideoToYoutubeOutput(
            youtube_video_id=youtube_video_id,
            youtube_video_url=youtube_video_url,
        )

    @staticmethod
    def _record_upload_completed(
        job_id: str, youtube_video_id: str, youtube_video_url: str
    ) -> None:
        from jobs.models import EventType, VideoJobEvent

        VideoJobEvent.objects.create(
            job_id=int(job_id),
            event_type=EventType.YOUTUBE_UPLOAD_COMPLETED,
            step_name="UPLOAD_YOUTUBE",
            message=f"YouTubeアップロード完了: {youtube_video_url}",
            payload_json={
                "youtube_video_id": youtube_video_id,
                "youtube_video_url": youtube_video_url,
            },
        )

    # ── set_thumbnail（YouTube API）──────────────────────────────

    async def set_thumbnail(self, input: SetThumbnailInput) -> SetThumbnailOutput:
        logger.info(
            "set_thumbnail  job_id=%s  yt_id=%s",
            input.job_id, input.youtube_video_id,
        )
        await self._youtube_api.set_thumbnail(
            access_token=input.access_token,
            youtube_video_id=input.youtube_video_id,
            thumbnail_url=input.thumbnail_url,
        )
        return SetThumbnailOutput(success=True)

    # ── apply_publish_settings（YouTube API）─────────────────────

    async def apply_publish_settings(
        self, input: ApplyPublishSettingsInput
    ) -> ApplyPublishSettingsOutput:
        logger.info(
            "apply_publish_settings  job_id=%s  yt_id=%s  mode=%s",
            input.job_id, input.youtube_video_id, input.publish_mode,
        )
        await self._youtube_api.update_video_privacy(
            access_token=input.access_token,
            youtube_video_id=input.youtube_video_id,
            privacy_status=input.publish_mode,
        )
        return ApplyPublishSettingsOutput(success=True, applied_status=input.publish_mode)

    # ── save_publish_result（DB 更新）────────────────────────────

    async def save_publish_result(
        self, input: SavePublishResultInput
    ) -> SavePublishResultOutput:
        logger.info(
            "save_publish_result  job_id=%s  yt_id=%s",
            input.job_id, input.youtube_video_id,
        )
        await sync_to_async(self._save_publish_result_sync)(input)
        return SavePublishResultOutput(success=True)

    def _save_publish_result_sync(self, input: SavePublishResultInput) -> None:
        from jobs.models import EventType, JobStatus, VideoJob, VideoJobEvent

        VideoJob.objects.filter(id=int(input.job_id)).update(
            status=JobStatus.COMPLETED,
            youtube_video_id=input.youtube_video_id,
            youtube_video_url=input.youtube_video_url,
            completed_at=datetime.now(tz=timezone.utc),
        )
        VideoJobEvent.objects.create(
            job_id=int(input.job_id),
            event_type=EventType.JOB_COMPLETED,
            message=f"YouTube投稿完了: {input.youtube_video_url}",
            payload_json={
                "youtube_video_id": input.youtube_video_id,
                "youtube_video_url": input.youtube_video_url,
                "publish_mode": input.publish_mode,
            },
        )
