"""
Pika 向けコンテンツバリデーター。

バリデーション順序:
  1. 共通チェック（validate_image_common / validate_audio_common）
  2. Pika 固有チェック

Pika 固有ルール:
  画像:
    - MIME: image/jpeg | image/png | image/webp | image/gif | image/avif （必須）
    - URL 入力前提
    - 最終出力は 720p〜1080p に変換される前提
    - ただし入力素材として不適切なケース（極端に低解像度など）は弾く

  音声:
    - API の直接入力仕様が明確でないため not_supported として扱う
    - 将来、仕様が確定した場合は _validate_audio を実装すること
"""
from __future__ import annotations

from aivideo_component.validation import constants as C
from aivideo_component.validation.common import (
    validate_audio_common,
    validate_image_common,
)
from aivideo_component.validation.protocol import (
    ContentValidationInput,
    ContentValidationResult,
)


class PikaContentValidator:
    """Pika 向けコンテンツバリデーター。"""

    def validate(self, input: ContentValidationInput) -> ContentValidationResult:
        result = ContentValidationResult(is_valid=True)

        if input.image is not None:
            validate_image_common(input.image, result)
            self._validate_image(input, result)

        if input.audio is not None:
            validate_audio_common(input.audio, result)
            self._mark_audio_unsupported(result)

        return result

    # ── 画像 ─────────────────────────────────────────────────────

    def _validate_image(
        self, input: ContentValidationInput, result: ContentValidationResult
    ) -> None:
        img = input.image
        if img is None:
            return

        # ── 必須: MIME タイプ ───────────────────────────────────
        # PIKA_IMAGE_ALLOWED_MIME は COMMON_IMAGE_ALLOWED_MIME の上位互換（gif/avif を追加）。
        # 共通を通過した MIME は必ず Pika でも通過するため、重複エラーは発生しない。
        # 共通で弾かれた MIME には共通エラーが既に出ているため重複させない。
        # → 共通を通過したが Pika が非対応の形式のみエラーを追加する（現状は該当なし）。
        if (img.mime_type
                and img.mime_type in C.COMMON_IMAGE_ALLOWED_MIME
                and img.mime_type not in C.PIKA_IMAGE_ALLOWED_MIME):
            result.add_error(
                "image",
                f"Pika: 非対応の画像形式です: {img.mime_type!r}  "
                f"（Pika 対応: {', '.join(sorted(C.PIKA_IMAGE_ALLOWED_MIME))}）",
            )

        # ── 必須: 入力素材として最低限の解像度 ──────────────────
        # Pika は最終的に 720p/1080p に変換するが、
        # 入力が極端に小さい場合は生成品質が著しく低下するため弾く
        for dim_name, dim_val in [("幅", img.width), ("高さ", img.height)]:
            if dim_val is not None and dim_val < C.PIKA_IMAGE_MIN_DIMENSION:
                result.add_error(
                    "image",
                    f"Pika: 画像の{dim_name}が小さすぎます: {dim_val}px  "
                    f"（入力素材として最小 {C.PIKA_IMAGE_MIN_DIMENSION}px 必要）",
                )

    # ── 音声 ─────────────────────────────────────────────────────

    def _mark_audio_unsupported(self, result: ContentValidationResult) -> None:
        """Pika は音声の直接入力 API 仕様が明確でないため not_supported として扱う。"""
        result.is_unsupported = True
        result.add_error(
            "audio",
            "Pika: 音声の直接入力は現時点では未対応です  "
            "（API 仕様確定後に実装予定）",
        )
