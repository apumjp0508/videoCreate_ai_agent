"""
YoutubePublishWorkflow が使う Activity のインターフェース定義。

Workflow はここだけを参照する。実装（dummy / 本番）は一切知らない。

ルール:
  - 各 Activity は専用の Input / Output dataclass を持つ
  - Activity スタブ関数は raise NotImplementedError のみ
  - 実装ファイルは @activity.defn(name="<同じ名前>") で同一名を登録すること
  - フィールド追加は末尾に default 付きで追加する（後方互換）

Activity 一覧:
  1. fetch_youtube_account     ─ YouTubeアカウント情報取得
  2. fetch_oauth_token         ─ OAuthトークン取得
  3. refresh_access_token      ─ アクセストークン更新
  4. fetch_publish_settings    ─ 投稿設定取得
  5. build_upload_request      ─ アップロード要求データ作成
  6. upload_video_to_youtube   ─ YouTube動画アップロード実行
  7. set_thumbnail             ─ サムネイル設定（任意）
  8. apply_publish_settings    ─ 公開設定反映（任意）
  9. save_publish_result       ─ 投稿結果保存
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from temporalio import activity


# ─────────────────────────────────────────────────────────────
# 1. fetch_youtube_account  ─ YouTubeアカウント情報取得
# ─────────────────────────────────────────────────────────────

@dataclass
class FetchYoutubeAccountInput:
    job_id: str
    user_id: int
    youtube_channel_id: str


@dataclass
class FetchYoutubeAccountOutput:
    channel_id: str
    channel_title: str
    # TODO: 本実装ではチャンネル設定・デフォルト公開設定などを追加する
    channel_metadata: dict[str, Any] = field(default_factory=dict)


@activity.defn
async def fetch_youtube_account(input: FetchYoutubeAccountInput) -> FetchYoutubeAccountOutput:
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────
# 2. fetch_oauth_token  ─ OAuthトークン取得
# ─────────────────────────────────────────────────────────────

@dataclass
class FetchOAuthTokenInput:
    job_id: str
    oauth_record_id: int


@dataclass
class FetchOAuthTokenOutput:
    access_token: str
    refresh_token: str
    expires_at: str     # ISO 8601
    is_expired: bool = False


@activity.defn
async def fetch_oauth_token(input: FetchOAuthTokenInput) -> FetchOAuthTokenOutput:
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────
# 3. refresh_access_token  ─ アクセストークン更新
# ─────────────────────────────────────────────────────────────

@dataclass
class RefreshAccessTokenInput:
    job_id: str
    oauth_record_id: int
    refresh_token: str


@dataclass
class RefreshAccessTokenOutput:
    access_token: str
    new_expires_at: str  # ISO 8601
    # TODO: 本実装では新しい refresh_token が発行された場合の保存処理を追加する


@activity.defn
async def refresh_access_token(input: RefreshAccessTokenInput) -> RefreshAccessTokenOutput:
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────
# 4. fetch_publish_settings  ─ 投稿設定取得
# ─────────────────────────────────────────────────────────────

@dataclass
class FetchPublishSettingsInput:
    job_id: str
    user_id: int
    # Workflow 入力から渡された設定（DB になければデフォルト値として使う）
    title_override: str = ""
    description_override: str = ""
    tags_override: list[str] = field(default_factory=list)
    publish_mode_override: str = "private"


@dataclass
class FetchPublishSettingsOutput:
    title: str
    description: str
    tags: list[str] = field(default_factory=list)
    category_id: str = "22"     # YouTube カテゴリ ID（22 = People & Blogs）
    publish_mode: str = "private"
    # TODO: 本実装では DB の投稿テンプレートから取得する


@activity.defn
async def fetch_publish_settings(input: FetchPublishSettingsInput) -> FetchPublishSettingsOutput:
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────
# 5. build_upload_request  ─ アップロード要求データ作成
# ─────────────────────────────────────────────────────────────

@dataclass
class BuildUploadRequestInput:
    job_id: str
    video_url: str
    channel_id: str
    title: str
    description: str
    tags: list[str] = field(default_factory=list)
    category_id: str = "22"
    publish_mode: str = "private"


@dataclass
class BuildUploadRequestOutput:
    """YouTube Data API v3 へ渡すリクエストデータ。"""
    # TODO: 本実装では YouTube API のスキーマに合わせた構造体に変更する
    upload_request: dict[str, Any] = field(default_factory=dict)
    video_url: str = ""


@activity.defn
async def build_upload_request(input: BuildUploadRequestInput) -> BuildUploadRequestOutput:
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────
# 6. upload_video_to_youtube  ─ YouTube動画アップロード実行
# ─────────────────────────────────────────────────────────────

@dataclass
class UploadVideoToYoutubeInput:
    job_id: str
    access_token: str
    upload_request: dict[str, Any] = field(default_factory=dict)
    video_url: str = ""


@dataclass
class UploadVideoToYoutubeOutput:
    youtube_video_id: str
    youtube_video_url: str


@activity.defn
async def upload_video_to_youtube(input: UploadVideoToYoutubeInput) -> UploadVideoToYoutubeOutput:
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────
# 7. set_thumbnail  ─ サムネイル設定（任意）
# ─────────────────────────────────────────────────────────────

@dataclass
class SetThumbnailInput:
    job_id: str
    youtube_video_id: str
    access_token: str
    thumbnail_url: str = ""


@dataclass
class SetThumbnailOutput:
    success: bool = True
    # TODO: 本実装では YouTube API のレスポンスを保存する


@activity.defn
async def set_thumbnail(input: SetThumbnailInput) -> SetThumbnailOutput:
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────
# 8. apply_publish_settings  ─ 公開設定反映（任意）
# ─────────────────────────────────────────────────────────────

@dataclass
class ApplyPublishSettingsInput:
    job_id: str
    youtube_video_id: str
    access_token: str
    publish_mode: str = "private"   # "private" | "unlisted" | "public"


@dataclass
class ApplyPublishSettingsOutput:
    success: bool = True
    applied_status: str = "private"


@activity.defn
async def apply_publish_settings(input: ApplyPublishSettingsInput) -> ApplyPublishSettingsOutput:
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────
# 9. save_publish_result  ─ 投稿結果保存
# ─────────────────────────────────────────────────────────────

@dataclass
class SavePublishResultInput:
    job_id: str
    youtube_video_id: str
    youtube_video_url: str
    publish_mode: str = "private"


@dataclass
class SavePublishResultOutput:
    success: bool = True
    # TODO: 本実装では保存した DB レコードの id などを返す


@activity.defn
async def save_publish_result(input: SavePublishResultInput) -> SavePublishResultOutput:
    raise NotImplementedError
