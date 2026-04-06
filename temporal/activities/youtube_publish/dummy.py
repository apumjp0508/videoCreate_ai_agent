"""
YoutubePublish Activity のダミー実装。

構成:
  - DummyYoutubePublishService: YoutubePublishServiceProtocol のダミー実装
  - dummy_* 関数群: @activity.defn(name=...) で登録する Activity 関数
    各関数は DummyYoutubePublishService に処理を委譲する

差し替え方:
  本番実装では RealYoutubePublishService を作り、
  worker_pipeline.py の _service = の部分を差し替えるだけでよい。
"""
import asyncio
import logging

from temporalio import activity

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

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# ダミーサービス実装
# ─────────────────────────────────────────────────────────────

class DummyYoutubePublishService:
    """
    YoutubePublishServiceProtocol のダミー実装。
    すべてのメソッドが固定値を返す。
    """

    async def fetch_youtube_account(self, input: FetchYoutubeAccountInput) -> FetchYoutubeAccountOutput:
        logger.info("[Dummy] fetch_youtube_account  job_id=%s  channel=%s", input.job_id, input.youtube_channel_id)
        await asyncio.sleep(0.05)
        return FetchYoutubeAccountOutput(
            channel_id=input.youtube_channel_id or "UC_dummy_channel_id",
            channel_title="Dummy Channel",
            channel_metadata={"subscriber_count": 1000},
        )

    async def fetch_oauth_token(self, input: FetchOAuthTokenInput) -> FetchOAuthTokenOutput:
        logger.info("[Dummy] fetch_oauth_token  job_id=%s  oauth_id=%s", input.job_id, input.oauth_record_id)
        await asyncio.sleep(0.05)
        return FetchOAuthTokenOutput(
            access_token="dummy_access_token_xxxxxx",
            refresh_token="dummy_refresh_token_yyyyyy",
            expires_at="2099-12-31T23:59:59Z",
            is_expired=False,
        )

    async def refresh_access_token(self, input: RefreshAccessTokenInput) -> RefreshAccessTokenOutput:
        logger.info("[Dummy] refresh_access_token  job_id=%s", input.job_id)
        await asyncio.sleep(0.05)
        return RefreshAccessTokenOutput(
            access_token="dummy_refreshed_access_token_xxxxxx",
            new_expires_at="2099-12-31T23:59:59Z",
        )

    async def fetch_publish_settings(self, input: FetchPublishSettingsInput) -> FetchPublishSettingsOutput:
        logger.info("[Dummy] fetch_publish_settings  job_id=%s  user_id=%s", input.job_id, input.user_id)
        await asyncio.sleep(0.05)
        return FetchPublishSettingsOutput(
            title=input.title_override or f"[Dummy] Video {input.job_id[:8]}",
            description=input.description_override or "This is a dummy video description.",
            tags=input.tags_override or ["dummy", "test"],
            category_id="22",
            publish_mode=input.publish_mode_override,
        )

    async def build_upload_request(self, input: BuildUploadRequestInput) -> BuildUploadRequestOutput:
        logger.info("[Dummy] build_upload_request  job_id=%s", input.job_id)
        await asyncio.sleep(0.05)
        return BuildUploadRequestOutput(
            upload_request={
                "snippet": {
                    "title": input.title,
                    "description": input.description,
                    "tags": input.tags,
                    "categoryId": input.category_id,
                    "channelId": input.channel_id,
                },
                "status": {
                    "privacyStatus": input.publish_mode,
                },
            },
            video_url=input.video_url,
        )

    async def upload_video_to_youtube(self, input: UploadVideoToYoutubeInput) -> UploadVideoToYoutubeOutput:
        logger.info("[Dummy] upload_video_to_youtube  job_id=%s", input.job_id)
        await asyncio.sleep(0.1)
        yt_id = f"dummy_yt_{input.job_id[:8]}"
        return UploadVideoToYoutubeOutput(
            youtube_video_id=yt_id,
            youtube_video_url=f"https://www.youtube.com/watch?v={yt_id}",
        )

    async def set_thumbnail(self, input: SetThumbnailInput) -> SetThumbnailOutput:
        logger.info("[Dummy] set_thumbnail  job_id=%s  yt_id=%s", input.job_id, input.youtube_video_id)
        await asyncio.sleep(0.05)
        return SetThumbnailOutput(success=True)

    async def apply_publish_settings(self, input: ApplyPublishSettingsInput) -> ApplyPublishSettingsOutput:
        logger.info("[Dummy] apply_publish_settings  job_id=%s  mode=%s", input.job_id, input.publish_mode)
        await asyncio.sleep(0.05)
        return ApplyPublishSettingsOutput(success=True, applied_status=input.publish_mode)

    async def save_publish_result(self, input: SavePublishResultInput) -> SavePublishResultOutput:
        logger.info(
            "[Dummy] save_publish_result  job_id=%s  yt_id=%s  url=%s",
            input.job_id, input.youtube_video_id, input.youtube_video_url,
        )
        await asyncio.sleep(0.05)
        return SavePublishResultOutput(success=True)


# ─────────────────────────────────────────────────────────────
# Activity 関数（worker_pipeline.py で登録する）
# ─────────────────────────────────────────────────────────────

_service = DummyYoutubePublishService()


@activity.defn(name="fetch_youtube_account")
async def dummy_fetch_youtube_account(input: FetchYoutubeAccountInput) -> FetchYoutubeAccountOutput:
    return await _service.fetch_youtube_account(input)


@activity.defn(name="fetch_oauth_token")
async def dummy_fetch_oauth_token(input: FetchOAuthTokenInput) -> FetchOAuthTokenOutput:
    return await _service.fetch_oauth_token(input)


@activity.defn(name="refresh_access_token")
async def dummy_refresh_access_token(input: RefreshAccessTokenInput) -> RefreshAccessTokenOutput:
    return await _service.refresh_access_token(input)


@activity.defn(name="fetch_publish_settings")
async def dummy_fetch_publish_settings(input: FetchPublishSettingsInput) -> FetchPublishSettingsOutput:
    return await _service.fetch_publish_settings(input)


@activity.defn(name="build_upload_request")
async def dummy_build_upload_request(input: BuildUploadRequestInput) -> BuildUploadRequestOutput:
    return await _service.build_upload_request(input)


@activity.defn(name="upload_video_to_youtube")
async def dummy_upload_video_to_youtube(input: UploadVideoToYoutubeInput) -> UploadVideoToYoutubeOutput:
    return await _service.upload_video_to_youtube(input)


@activity.defn(name="set_thumbnail")
async def dummy_set_thumbnail(input: SetThumbnailInput) -> SetThumbnailOutput:
    return await _service.set_thumbnail(input)


@activity.defn(name="apply_publish_settings")
async def dummy_apply_publish_settings(input: ApplyPublishSettingsInput) -> ApplyPublishSettingsOutput:
    return await _service.apply_publish_settings(input)


@activity.defn(name="save_publish_result")
async def dummy_save_publish_result(input: SavePublishResultInput) -> SavePublishResultOutput:
    return await _service.save_publish_result(input)
