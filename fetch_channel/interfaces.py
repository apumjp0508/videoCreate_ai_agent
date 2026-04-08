"""
fetch_channel インターフェース定義。

呼び出し側はここだけを参照する。実装（mock / 本番）は一切知らない。

ルール:
  - FetchChannelClient は Protocol として定義する（DI・テスト置換が容易）
  - ChannelInfo はフラットな dataclass にして YouTube API の生 dict を隠蔽する
  - 実装ファイルは FetchChannelClient を満たすクラスを定義すること
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class ChannelInfo:
    """
    1 件分のYouTubeチャンネル情報。
    YouTube Data API の items[].snippet / contentDetails / statistics を正規化したもの。
    """
    id: str
    title: str
    handle: str                  # snippet.customUrl（例: @mychannel）
    thumbnail_url: str = ''
    description: str = ''        # snippet.description
    country: str = ''            # snippet.country
    uploads_playlist_id: str = '' # contentDetails.relatedPlaylists.uploads
    subscriber_count: int | None = None   # statistics.subscriberCount
    video_count: int | None = None        # statistics.videoCount
    view_count: int | None = None         # statistics.viewCount

    def to_dict(self) -> dict:
        """セッション保存用の JSON シリアライズ可能な dict に変換する。"""
        return {
            'id': self.id,
            'title': self.title,
            'handle': self.handle,
            'thumbnail_url': self.thumbnail_url,
            'description': self.description,
            'country': self.country,
            'uploads_playlist_id': self.uploads_playlist_id,
            'subscriber_count': self.subscriber_count,
            'video_count': self.video_count,
            'view_count': self.view_count,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ChannelInfo:
        """セッションから復元するためのファクトリ。"""
        return cls(
            id=d.get('id', ''),
            title=d.get('title', ''),
            handle=d.get('handle', ''),
            thumbnail_url=d.get('thumbnail_url', ''),
            description=d.get('description', ''),
            country=d.get('country', ''),
            uploads_playlist_id=d.get('uploads_playlist_id', ''),
            subscriber_count=d.get('subscriber_count'),
            video_count=d.get('video_count'),
            view_count=d.get('view_count'),
        )


@runtime_checkable
class FetchChannelClient(Protocol):
    """
    アクセストークンを使って YouTube チャンネル一覧を取得するクライアントの契約。

    実装クラスはこの Protocol を満たせばよい（明示的な継承不要）。
    """

    def fetch(self, token: str) -> list[ChannelInfo]:
        """
        token: YouTube Data API アクセストークン
        戻り値: 取得したチャンネル一覧（0 件の場合は空リスト）
        """
        ...
