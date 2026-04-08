"""
VideoGenerationWorkflow が使う Activity のインターフェース定義。

Workflow はここだけを参照する。実装（dummy / 本番）は一切知らない。

ルール:
  - 各 Activity は専用の Input / Output dataclass を持つ
  - Activity スタブ関数は raise NotImplementedError のみ
  - 実装ファイルは @activity.defn(name="<同じ名前>") で同一名を登録すること
  - フィールド追加は末尾に default 付きで追加する（後方互換）

Activity 一覧:
  1. fetch_materials           ─ 素材取得
  2. fetch_ai_config           ─ AI設定取得
  3. fetch_request_definition  ─ リクエスト定義取得
  4. build_ai_request          ─ AIリクエスト生成
  5. submit_ai_request         ─ AIへ送信
  6. poll_generation_status    ─ 生成状況確認
  7. fetch_generated_video     ─ 完成動画取得
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from temporalio import activity


# ─────────────────────────────────────────────────────────────
# 1. fetch_materials  ─ 素材取得
# ─────────────────────────────────────────────────────────────

@dataclass
class ImageMaterial:
    """
    画像素材の詳細情報。
    GeneratedImage モデルのフィールドに対応する。
    """
    id: int
    title: str
    file_url: str           # Django storage URL（例: /media/images/xxx.jpg）
    mime_type: str = ""
    width: int = 0
    height: int = 0
    aspect_ratio: str = ""  # 例: "16:9", "1:1", "9:16"
    file_size_bytes: int = 0
    description: str = ""


@dataclass
class AudioMaterial:
    """
    音声素材の詳細情報。
    GeneratedAudio モデルのフィールドに対応する。
    """
    id: int
    title: str
    file_url: str           # Django storage URL（例: /media/audios/xxx.mp3）
    mime_type: str = ""
    duration_sec: float = 0.0
    sample_rate: int = 0
    channels: int = 0       # 1=モノラル, 2=ステレオ
    codec: str = ""         # 例: "mp3", "aac", "wav"
    file_size_bytes: int = 0
    description: str = ""


@dataclass
class FetchMaterialsInput:
    job_id: str
    user_id: int
    image_ids: list[int] = field(default_factory=list)
    audio_ids: list[int] = field(default_factory=list)


@dataclass
class FetchMaterialsOutput:
    """取得した素材データ。images / audios に詳細情報が入る。"""
    image_ids: list[int] = field(default_factory=list)
    audio_ids: list[int] = field(default_factory=list)
    images: list[ImageMaterial] = field(default_factory=list)
    audios: list[AudioMaterial] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@activity.defn
async def fetch_materials(input: FetchMaterialsInput) -> FetchMaterialsOutput:
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────
# 2. fetch_ai_config  ─ AI設定取得
# ─────────────────────────────────────────────────────────────

@dataclass
class FetchAiConfigInput:
    job_id: str
    credential_id: int
    model_id: int


@dataclass
class FetchAiConfigOutput:
    """AI プロバイダーへの接続設定。"""
    config_id: int
    model_name: str
    api_endpoint: str
    # credential_id は submit_ai_request が DB から API キーを安全に取得するために使う
    # Temporal ヒストリに API キー本体は含めない
    credential_id: int = 0
    params: dict[str, Any] = field(default_factory=dict)


@activity.defn
async def fetch_ai_config(input: FetchAiConfigInput) -> FetchAiConfigOutput:
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────
# 3. fetch_request_definition  ─ リクエスト定義取得
# ─────────────────────────────────────────────────────────────

@dataclass
class FetchRequestDefinitionInput:
    job_id: str
    prompt_id: int


@dataclass
class FetchRequestDefinitionOutput:
    """プロンプトテーブルから取得したリクエスト定義。"""
    prompt_id: int
    prompt_text: str
    # TODO: 本実装ではフォーマット設定・スタイル指定などを追加する
    format_settings: dict[str, Any] = field(default_factory=dict)


@activity.defn
async def fetch_request_definition(input: FetchRequestDefinitionInput) -> FetchRequestDefinitionOutput:
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────
# 4. build_ai_request  ─ AIリクエスト生成
# ─────────────────────────────────────────────────────────────

@dataclass
class BuildAiRequestInput:
    job_id: str
    model_name: str
    api_endpoint: str
    prompt_text: str
    image_ids: list[int] = field(default_factory=list)
    audio_ids: list[int] = field(default_factory=list)
    config_params: dict[str, Any] = field(default_factory=dict)
    format_settings: dict[str, Any] = field(default_factory=dict)


@dataclass
class BuildAiRequestOutput:
    """AI プロバイダーへ送信するリクエストペイロード。"""
    # TODO: 本実装では AI プロバイダーの API 仕様に合わせた構造体に変更する
    ai_request_payload: dict[str, Any] = field(default_factory=dict)


@activity.defn
async def build_ai_request(input: BuildAiRequestInput) -> BuildAiRequestOutput:
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────
# 5. submit_ai_request  ─ AIへ送信
# ─────────────────────────────────────────────────────────────

@dataclass
class SubmitAiRequestInput:
    job_id: str
    api_endpoint: str
    # API キーは Temporal ヒストリに含めず、Activity 内で credential_id から DB 取得する
    credential_id: int = 0
    ai_request_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class SubmitAiRequestOutput:
    """AI へのリクエスト送信結果。generation_id で生成ジョブを追跡する。"""
    generation_id: str
    initial_status: str = "pending"


@activity.defn
async def submit_ai_request(input: SubmitAiRequestInput) -> SubmitAiRequestOutput:
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────
# 6. poll_generation_status  ─ 生成状況確認（ループ用）
# ─────────────────────────────────────────────────────────────

@dataclass
class PollGenerationStatusInput:
    job_id: str
    generation_id: str


@dataclass
class PollGenerationStatusOutput:
    """
    生成状況。
    Workflow 側で is_complete が True になるまでループする。
    """
    generation_id: str
    status: str           # "pending" | "processing" | "completed" | "failed"
    is_complete: bool = False
    is_failed: bool = False
    # 完成している場合のみ設定される
    video_url: str = ""


@activity.defn
async def poll_generation_status(input: PollGenerationStatusInput) -> PollGenerationStatusOutput:
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────
# 7. fetch_generated_video  ─ 完成動画取得
# ─────────────────────────────────────────────────────────────

@dataclass
class FetchGeneratedVideoInput:
    job_id: str
    generation_id: str
    video_url: str


@dataclass
class FetchGeneratedVideoOutput:
    """完成動画の情報。次の YoutubePublishWorkflow へ渡す。"""
    video_url: str
    # TODO: 本実装ではファイルサイズ・解像度・長さなどのメタデータを追加する
    video_metadata: dict[str, Any] = field(default_factory=dict)


@activity.defn
async def fetch_generated_video(input: FetchGeneratedVideoInput) -> FetchGeneratedVideoOutput:
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────
# 8. save_generated_video  ─ 完成動画を media に保存して DB に記録
# ─────────────────────────────────────────────────────────────

@dataclass
class SaveGeneratedVideoInput:
    """
    AI プロバイダーが返した動画 URL をダウンロードして Django media に保存する。

    job_id:          対象 VideoJob の PK（文字列）
    generation_id:   AI プロバイダー側の生成ジョブ ID
    video_url:       ダウンロード元 URL（AI プロバイダーの一時 URL）
    video_metadata:  fetch_generated_video が返したメタデータ
                     （duration_sec / resolution / format 等）
    """
    job_id: str
    generation_id: str
    video_url: str
    video_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SaveGeneratedVideoOutput:
    """
    media に保存された動画の情報。

    generated_video_id : jobs.GeneratedVideo の PK
    media_url          : Django media 経由でアクセス可能な絶対 URL
                         （YoutubePublishWorkflow の video_url として使用する）
    """
    generated_video_id: int
    media_url: str


@activity.defn
async def save_generated_video(
    input: SaveGeneratedVideoInput,
) -> SaveGeneratedVideoOutput:
    raise NotImplementedError
