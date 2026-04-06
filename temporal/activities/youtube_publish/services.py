"""
YoutubePublish サービス層の Protocol（抽象インターフェース）定義。

設計意図:
  - Activity 関数はこの Protocol に準拠したサービスオブジェクトに処理を委譲する
  - YouTube API の実装を差し替えても Workflow / Activity 層は変わらない
  - テスト時はモックサービスを差し込める
  - 将来 OAuth プロバイダーが変わっても対応しやすい

使い方:
  1. この Protocol を実装するクラスを作る（DummyYoutubePublishService など）
  2. dummy.py や本番 activities.py から _service として参照する
  3. worker_pipeline.py で差し替える
"""
from __future__ import annotations

from typing import Protocol

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


class YoutubePublishServiceProtocol(Protocol):
    """
    YouTube 投稿に必要なすべての処理を担うサービスの契約。
    Activity 実装はこの Protocol に依存する。
    """

    async def fetch_youtube_account(
        self, input: FetchYoutubeAccountInput
    ) -> FetchYoutubeAccountOutput:
        """DB から YouTube チャンネル情報を取得する。"""
        ...

    async def fetch_oauth_token(
        self, input: FetchOAuthTokenInput
    ) -> FetchOAuthTokenOutput:
        """DB から保存済み OAuth トークンを取得する。"""
        ...

    async def refresh_access_token(
        self, input: RefreshAccessTokenInput
    ) -> RefreshAccessTokenOutput:
        """Google OAuth エンドポイントへリフレッシュリクエストを送り、新トークンを返す。"""
        ...

    async def fetch_publish_settings(
        self, input: FetchPublishSettingsInput
    ) -> FetchPublishSettingsOutput:
        """DB から投稿テンプレート（タイトル・説明・タグ等）を取得する。"""
        ...

    async def build_upload_request(
        self, input: BuildUploadRequestInput
    ) -> BuildUploadRequestOutput:
        """YouTube Data API v3 へ渡すリクエストデータを組み立てる。"""
        ...

    async def upload_video_to_youtube(
        self, input: UploadVideoToYoutubeInput
    ) -> UploadVideoToYoutubeOutput:
        """YouTube API へ動画をアップロードする。"""
        ...

    async def set_thumbnail(
        self, input: SetThumbnailInput
    ) -> SetThumbnailOutput:
        """YouTube API でサムネイルを設定する。"""
        ...

    async def apply_publish_settings(
        self, input: ApplyPublishSettingsInput
    ) -> ApplyPublishSettingsOutput:
        """YouTube API で公開設定（公開 / 限定公開 / 非公開）を変更する。"""
        ...

    async def save_publish_result(
        self, input: SavePublishResultInput
    ) -> SavePublishResultOutput:
        """アップロード結果を DB に保存する。"""
        ...
