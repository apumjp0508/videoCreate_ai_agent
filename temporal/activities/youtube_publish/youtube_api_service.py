"""
YouTube Data API v3 サービス層。

設計方針:
  - YoutubeApiServiceProtocol で「YouTube API への操作」を抽象化する
  - YoutubeDataApiService が具体実装（urllib 使用、非同期は asyncio.to_thread で対応）
  - DB 操作はここに含めない（DjangoYoutubePublishService が担う）
  - 差し替え可能にしておくことでテスト時はモックに切り替えられる

YouTube Data API v3 エンドポイント:
  - Videos.insert  (resumable upload)
  - Thumbnails.set (multipart upload)
  - Videos.update  (privacy 変更)
  - Token refresh  (Google OAuth 2.0)
"""
from __future__ import annotations

import asyncio
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Protocol

logger = logging.getLogger(__name__)

# ── YouTube / Google API 定数 ─────────────────────────────────

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
YT_VIDEOS_INSERT_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
YT_VIDEOS_UPDATE_URL = "https://www.googleapis.com/youtube/v3/videos"
YT_THUMBNAILS_SET_URL = "https://www.googleapis.com/upload/youtube/v3/thumbnails/set"


# ─────────────────────────────────────────────────────────────
# Protocol（抽象インターフェース）
# ─────────────────────────────────────────────────────────────

class YoutubeApiServiceProtocol(Protocol):
    """
    YouTube Data API v3 への操作を抽象化するインターフェース。

    各メソッドは YouTube / Google API の単一操作に対応する。
    DB 操作は含まない。テスト時はこの Protocol を満たすモックに差し替える。
    """

    async def call_refresh_token(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ) -> dict:
        """
        Google OAuth 2.0 エンドポイントでアクセストークンを更新する。

        Returns:
            {"access_token": str, "expires_in": int, "token_type": str}
        """
        ...

    async def upload_video(
        self,
        access_token: str,
        metadata: dict,
        video_url: str,
    ) -> str:
        """
        YouTube に動画をアップロードして YouTube 動画 ID を返す。

        Args:
            metadata: YouTube Data API の snippet + status 構造体
            video_url: アップロードする動画ファイルの URL
        Returns:
            YouTube 動画 ID (例: "dQw4w9WgXcQ")
        """
        ...

    async def set_thumbnail(
        self,
        access_token: str,
        youtube_video_id: str,
        thumbnail_url: str,
    ) -> None:
        """サムネイル画像を YouTube 動画に設定する。"""
        ...

    async def update_video_privacy(
        self,
        access_token: str,
        youtube_video_id: str,
        privacy_status: str,
    ) -> None:
        """YouTube 動画のプライバシー設定（public / unlisted / private）を更新する。"""
        ...


# ─────────────────────────────────────────────────────────────
# 具体実装
# ─────────────────────────────────────────────────────────────

class YoutubeDataApiService:
    """
    YoutubeApiServiceProtocol の YouTube Data API v3 実装。

    HTTP 通信は urllib (stdlib) を使い、asyncio.to_thread でスレッド実行する。
    大容量動画の Resumable Upload に対応。
    """

    async def call_refresh_token(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ) -> dict:
        logger.info("call_refresh_token: refreshing access token")
        return await asyncio.to_thread(
            self._call_refresh_token_sync, client_id, client_secret, refresh_token
        )

    def _call_refresh_token_sync(
        self, client_id: str, client_secret: str, refresh_token: str
    ) -> dict:
        data = urllib.parse.urlencode({
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }).encode()
        req = urllib.request.Request(GOOGLE_TOKEN_URL, data=data, method="POST")
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    # ── upload_video ────────────────────────────────────────────

    async def upload_video(
        self,
        access_token: str,
        metadata: dict,
        video_url: str,
    ) -> str:
        logger.info("upload_video: starting resumable upload  video_url=%s", video_url)
        return await asyncio.to_thread(
            self._upload_video_sync, access_token, metadata, video_url
        )

    def _upload_video_sync(
        self, access_token: str, metadata: dict, video_url: str
    ) -> str:
        # Step 1: Resumable Upload セッションを開始してアップロード URL を取得
        upload_url = self._initiate_resumable_upload(access_token, metadata)

        # Step 2: 動画データをダウンロードして YouTube へアップロード
        video_data, content_type = self._download_file(video_url)
        return self._execute_upload(access_token, upload_url, video_data, content_type)

    def _initiate_resumable_upload(self, access_token: str, metadata: dict) -> str:
        """YouTube に Resumable Upload セッションを開始させ、アップロード URL を返す。"""
        params = urllib.parse.urlencode({
            "uploadType": "resumable",
            "part": "snippet,status",
        })
        url = f"{YT_VIDEOS_INSERT_URL}?{params}"
        data = json.dumps(metadata).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": "video/*",
            },
        )
        with urllib.request.urlopen(req) as resp:
            upload_url = resp.headers.get("Location")
            if not upload_url:
                raise RuntimeError("YouTube Resumable Upload: Location header missing")
            return upload_url

    def _execute_upload(
        self,
        access_token: str,
        upload_url: str,
        video_data: bytes,
        content_type: str,
    ) -> str:
        """動画データを YouTube にアップロードして動画 ID を返す。"""
        req = urllib.request.Request(
            upload_url,
            data=video_data,
            method="PUT",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Length": str(len(video_data)),
                "Content-Type": content_type or "video/*",
            },
        )
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            return result["id"]

    # ── set_thumbnail ────────────────────────────────────────────

    async def set_thumbnail(
        self,
        access_token: str,
        youtube_video_id: str,
        thumbnail_url: str,
    ) -> None:
        logger.info("set_thumbnail  yt_id=%s  url=%s", youtube_video_id, thumbnail_url)
        await asyncio.to_thread(
            self._set_thumbnail_sync, access_token, youtube_video_id, thumbnail_url
        )

    def _set_thumbnail_sync(
        self, access_token: str, youtube_video_id: str, thumbnail_url: str
    ) -> None:
        image_data, content_type = self._download_file(thumbnail_url)
        params = urllib.parse.urlencode({"videoId": youtube_video_id, "uploadType": "media"})
        url = f"{YT_THUMBNAILS_SET_URL}?{params}"
        req = urllib.request.Request(
            url,
            data=image_data,
            method="POST",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": content_type or "image/jpeg",
                "Content-Length": str(len(image_data)),
            },
        )
        with urllib.request.urlopen(req):
            pass  # 200 OK で成功

    # ── update_video_privacy ─────────────────────────────────────

    async def update_video_privacy(
        self,
        access_token: str,
        youtube_video_id: str,
        privacy_status: str,
    ) -> None:
        logger.info(
            "update_video_privacy  yt_id=%s  status=%s",
            youtube_video_id, privacy_status,
        )
        await asyncio.to_thread(
            self._update_video_privacy_sync, access_token, youtube_video_id, privacy_status
        )

    def _update_video_privacy_sync(
        self, access_token: str, youtube_video_id: str, privacy_status: str
    ) -> None:
        params = urllib.parse.urlencode({"part": "status"})
        url = f"{YT_VIDEOS_UPDATE_URL}?{params}"
        body = json.dumps({
            "id": youtube_video_id,
            "status": {"privacyStatus": privacy_status},
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method="PUT",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
        )
        with urllib.request.urlopen(req):
            pass  # 200 OK で成功

    # ── 共通ユーティリティ ────────────────────────────────────────

    @staticmethod
    def _download_file(url: str) -> tuple[bytes, str]:
        """URL からファイルをダウンロードして (data, content_type) を返す。"""
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            content_type = resp.headers.get("Content-Type", "application/octet-stream")
            return data, content_type
