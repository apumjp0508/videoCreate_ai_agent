"""
FetchChannelClient の YouTube Data API v3 実装。

リクエスト例:
  curl -H "Authorization: Bearer <ACCESS_TOKEN>" \
    "https://www.googleapis.com/youtube/v3/channels?part=snippet,contentDetails,statistics&mine=true"

レスポンス構造 (items[]):
  {
    "id": "UCxxxxxxxx",
    "snippet": {
      "title": "...",
      "description": "...",
      "customUrl": "@handle",
      "country": "JP",
      "thumbnails": {
        "default": {"url": "..."},
        "medium":  {"url": "..."},
        "high":    {"url": "..."}
      }
    },
    "contentDetails": {
      "relatedPlaylists": {
        "uploads": "UUxxxxxxxx"
      }
    },
    "statistics": {
      "viewCount": "1000",
      "subscriberCount": "100",
      "hiddenSubscriberCount": false,
      "videoCount": "10"
    }
  }
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from fetch_channel.interfaces import ChannelInfo

logger = logging.getLogger(__name__)

YOUTUBE_CHANNELS_URL = 'https://www.googleapis.com/youtube/v3/channels'


class YouTubeApiFetchChannelClient:
    """
    YouTube Data API v3 の channels.list を呼び出してチャンネル一覧を取得する。

    part=snippet,contentDetails,statistics&mine=true で認証済みユーザーの
    チャンネルをすべて取得し ChannelInfo のリストに変換して返す。
    """

    def fetch(self, token: str) -> list[ChannelInfo]:
        """
        token: YouTube Data API アクセストークン（Bearer）
        戻り値: 取得したチャンネル一覧（0 件の場合は空リスト）

        Raises:
            urllib.error.HTTPError: API 呼び出しが 4xx / 5xx を返した場合
        """
        url = YOUTUBE_CHANNELS_URL + '?' + urllib.parse.urlencode({
            'part': 'snippet,contentDetails,statistics',
            'mine': 'true',
            'maxResults': 50,
        })
        req = urllib.request.Request(
            url,
            headers={'Authorization': f'Bearer {token}'},
        )

        logger.info('[YouTubeApiFetchChannelClient] channels.list を呼び出します')
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())

        items = data.get('items', [])
        logger.info('[YouTubeApiFetchChannelClient] %d 件取得しました', len(items))

        return [self._parse_item(item) for item in items]

    @staticmethod
    def _parse_item(item: dict) -> ChannelInfo:
        snippet = item.get('snippet', {})
        thumbnails = snippet.get('thumbnails', {})
        thumbnail_url = (
            thumbnails.get('high', {}).get('url', '')
            or thumbnails.get('medium', {}).get('url', '')
            or thumbnails.get('default', {}).get('url', '')
        )

        content_details = item.get('contentDetails', {})
        uploads_playlist_id = (
            content_details.get('relatedPlaylists', {}).get('uploads', '')
        )

        statistics = item.get('statistics', {})
        subscriber_count = _to_int(statistics.get('subscriberCount'))
        video_count = _to_int(statistics.get('videoCount'))
        view_count = _to_int(statistics.get('viewCount'))

        return ChannelInfo(
            id=item.get('id', ''),
            title=snippet.get('title', ''),
            handle=snippet.get('customUrl', ''),
            thumbnail_url=thumbnail_url,
            description=snippet.get('description', ''),
            country=snippet.get('country', ''),
            uploads_playlist_id=uploads_playlist_id,
            subscriber_count=subscriber_count,
            video_count=video_count,
            view_count=view_count,
        )


def _to_int(value: str | None) -> int | None:
    """YouTube API の統計値は文字列で返ってくるため int に変換する。None はそのまま返す。"""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
