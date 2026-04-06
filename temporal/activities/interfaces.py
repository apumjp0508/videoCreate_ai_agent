"""
Activity インターフェース定義。

Workflow はここだけを参照する。実装（dummy / 本番）は一切知らない。

追加ルール:
  - 各 Activity に専用の Input / Output dataclass を持たせる
  - 引数の追加は dataclass フィールドに default 付きで追加する（後方互換）
  - 実装ファイルは @activity.defn(name="<同じ名前>") で登録すること
"""
from __future__ import annotations

from dataclasses import dataclass, field
from temporalio import activity


# ─────────────────────────────────────────────────────────────
# generate_video_script
# ─────────────────────────────────────────────────────────────

@dataclass
class ScriptGenerationInput:
    job_id: str
    prompt_id: int


@dataclass
class ScriptGenerationOutput:
    script_text: str


@activity.defn
async def generate_video_script(input: ScriptGenerationInput) -> ScriptGenerationOutput:
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────
# generate_video
# ─────────────────────────────────────────────────────────────

@dataclass
class VideoGenerationInput:
    job_id: str
    script_text: str
    video_ai_config_id: int
    image_ids: list[int] = field(default_factory=list)
    audio_ids: list[int] = field(default_factory=list)


@dataclass
class VideoGenerationOutput:
    video_url: str


@activity.defn
async def generate_video(input: VideoGenerationInput) -> VideoGenerationOutput:
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────
# upload_to_youtube
# ─────────────────────────────────────────────────────────────

@dataclass
class YoutubeUploadInput:
    job_id: str
    video_url: str
    oauth_record_id: int
    youtube_channel_id: str
    publish_mode: str = "private"


@dataclass
class YoutubeUploadOutput:
    youtube_video_id: str
    youtube_video_url: str


@activity.defn
async def upload_to_youtube(input: YoutubeUploadInput) -> YoutubeUploadOutput:
    raise NotImplementedError
