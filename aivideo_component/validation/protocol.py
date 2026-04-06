"""
コンテンツバリデーションの共通型定義と Protocol。

設計方針:
  - バリデーターは Django モデルを知らない（疎結合）
  - View 側がモデルから ImageMeta / AudioMeta を組み立てて渡す
  - 各 AI サービスごとに Protocol 準拠のバリデーター実装を置く
  - 将来プロバイダーが増えても registry.py に1行追加するだけ

型の流れ:
  View
    └─ モデルから ContentValidationInput を組み立て
    └─ registry.get_validator(provider_key) でバリデーター取得
    └─ validator.validate(input) → ContentValidationResult
    └─ result.is_valid で分岐
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


# ─────────────────────────────────────────────────────────────
# コンテンツメタデータ（モデルから変換して渡す）
# ─────────────────────────────────────────────────────────────

@dataclass
class ImageMeta:
    """GeneratedImage から抽出した検証用メタデータ。"""
    image_id: int
    mime_type: str = ""
    file_size_bytes: int | None = None
    width: int | None = None
    height: int | None = None
    aspect_ratio: str = ""          # 例: "16:9", "1:1", "9:16"


@dataclass
class AudioMeta:
    """GeneratedAudio から抽出した検証用メタデータ。"""
    audio_id: int
    mime_type: str = ""
    file_size_bytes: int | None = None
    duration_sec: float | None = None
    sample_rate: int | None = None  # Hz
    channels: int | None = None     # 1=モノラル, 2=ステレオ
    codec: str = ""                 # 例: "mp3", "aac", "wav"


# ─────────────────────────────────────────────────────────────
# バリデーション入力
# ─────────────────────────────────────────────────────────────

@dataclass
class ContentValidationInput:
    """
    バリデーターに渡す入力。
    View が選択されたコンテンツと対象プロバイダーを組み立てて渡す。
    """
    provider_key: str               # "runway" | "pika" | "kling" など
    script: str = ""
    image: ImageMeta | None = None
    audio: AudioMeta | None = None


# ─────────────────────────────────────────────────────────────
# バリデーション結果
# ─────────────────────────────────────────────────────────────

@dataclass
class ValidationIssue:
    """1件の指摘事項（エラーまたは警告）。"""
    field: str      # "script" | "image" | "audio" | "general"
    message: str


@dataclass
class ContentValidationResult:
    """バリデーション全体の結果。"""
    is_valid: bool
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    def add_error(self, field: str, message: str) -> None:
        self.errors.append(ValidationIssue(field=field, message=message))
        self.is_valid = False

    def add_warning(self, field: str, message: str) -> None:
        self.warnings.append(ValidationIssue(field=field, message=message))


# ─────────────────────────────────────────────────────────────
# バリデーター Protocol（インターフェース）
# ─────────────────────────────────────────────────────────────

class ContentValidatorProtocol(Protocol):
    """
    各 AI プロバイダーのコンテンツバリデーターが準拠すべき契約。

    実装クラスは継承不要。このシグネチャと一致していれば自動的に準拠とみなされる。
    """

    def validate(self, input: ContentValidationInput) -> ContentValidationResult:
        """
        コンテンツがこのプロバイダーの要件を満たすか検証する。

        Args:
            input: バリデーション対象のコンテンツ情報
        Returns:
            ContentValidationResult: 結果。is_valid=False の場合は errors に詳細を持つ
        """
        ...
