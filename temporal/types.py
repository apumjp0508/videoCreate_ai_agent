"""
Temporal Workflow の入出力型定義。

変更方針:
  - フィールドを追加するときは末尾に追加し default=None を付ける
  - フィールドを削除・リネームするときは先に Optional[...] にして移行期間を設ける
  - 型を変える場合は新フィールドを追加してから旧フィールドを廃止する順で行う

NOTE: dataclass を使うのは Temporal SDK が JSON シリアライズに対応しているため。
      dict や Any は使わず、型を明示することで補完・静的解析が効く状態を保つ。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────
# Workflow 入力
# ─────────────────────────────────────────────────────────────

@dataclass
class VideoJobInput:
    # ジョブ識別
    job_id: str                          # Django 側で生成した UUID
    request_id: str                      # リクエスト単位の UUID (冪等キーとして使用)

    # 実行ユーザー / 設定
    user_id: int                         # accounts.User.id
    video_ai_config_id: int              # video_ai.UserVideoAiConfig.id

    # コンテンツ素材
    prompt_id: int                       # プロンプトテーブルの id
    image_ids: list[int] = field(default_factory=list)   # 使用する画像の id リスト
    audio_ids: list[int] = field(default_factory=list)   # 使用する音声の id リスト

    # YouTube 連携
    oauth_record_id: int = 0             # google_auth.OAuthRecord.id
    youtube_channel_id: str = ""         # YouTube チャンネル ID

    # 公開設定
    publish_mode: str = "private"        # "private" | "unlisted" | "public"


# ─────────────────────────────────────────────────────────────
# Workflow 出力
# ─────────────────────────────────────────────────────────────

@dataclass
class VideoJobOutput:
    job_id: str
    youtube_video_id: str                # アップロード後の YouTube 動画 ID
    youtube_video_url: str = ""          # https://www.youtube.com/watch?v=...
