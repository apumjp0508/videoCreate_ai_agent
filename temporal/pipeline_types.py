"""
VideoPipelineWorkflow / 子 Workflow の入出力 DTO 定義。

設計方針:
  - Workflow 間で渡されるデータはすべてここで一元管理する
  - Activity レベルの Input/Output は各 activities/*/interfaces.py に置く
  - フィールド追加は末尾に default 付きで追加する（後方互換）
  - dict/Any は使わず型を明示して補完・静的解析を維持する
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────
# VideoPipelineWorkflow  ─ 親 Workflow の入出力
# ─────────────────────────────────────────────────────────────

@dataclass
class PipelineInput:
    """
    VideoPipelineWorkflow への入力。
    Django 側で組み立てて Temporal Client から渡す。
    """
    # ジョブ識別
    job_id: str                             # Django で生成した UUID
    request_id: str                         # 冪等キー

    # ユーザー / AI 設定
    user_id: int
    credential_id: int
    model_id: int

    # コンテンツ素材
    prompt_id: int
    image_ids: list[int] = field(default_factory=list)
    audio_ids: list[int] = field(default_factory=list)

    # YouTube 連携
    oauth_record_id: int = 0
    youtube_channel_id: str = ""

    # 投稿設定
    # title / description / tags / thumbnail_url は YoutubePublishWorkflow 内の
    # fetch_publish_settings Activity が DB から取得するため、ここでは渡さない
    publish_mode: str = "private"           # "private" | "unlisted" | "public"


@dataclass
class PipelineOutput:
    """VideoPipelineWorkflow の最終結果。"""
    job_id: str
    youtube_video_id: str
    youtube_video_url: str = ""


# ─────────────────────────────────────────────────────────────
# VideoGenerationWorkflow  ─ 子 Workflow 1 の入出力
# ─────────────────────────────────────────────────────────────

@dataclass
class VideoGenerationWorkflowInput:
    """動画生成子 Workflow への入力。"""
    job_id: str
    user_id: int
    credential_id: int
    model_id: int
    prompt_id: int
    image_ids: list[int] = field(default_factory=list)
    audio_ids: list[int] = field(default_factory=list)


@dataclass
class VideoGenerationWorkflowOutput:
    """動画生成子 Workflow の出力。"""
    job_id: str
    video_url: str
    generation_id: str = ""


# ─────────────────────────────────────────────────────────────
# YoutubePublishWorkflow  ─ 子 Workflow 2 の入出力
# ─────────────────────────────────────────────────────────────

@dataclass
class YoutubePublishWorkflowInput:
    """YouTube 投稿子 Workflow への入力。"""
    job_id: str
    user_id: int
    video_url: str
    oauth_record_id: int
    youtube_channel_id: str
    publish_mode: str = "private"
    # title / description / tags / thumbnail_url は fetch_publish_settings Activity が取得する


@dataclass
class YoutubePublishWorkflowOutput:
    """YouTube 投稿子 Workflow の出力。"""
    job_id: str
    youtube_video_id: str
    youtube_video_url: str = ""
