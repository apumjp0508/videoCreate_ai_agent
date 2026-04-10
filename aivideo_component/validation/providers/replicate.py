"""
Replicate (minimax/video-01) 向けコンテンツバリデーター。

minimax/video-01 の入力仕様:
  画像 (first_frame_image):
    - URL 入力のみ対応（ファイルアップロード不可）
    - 対応 MIME: image/jpeg | image/png | image/webp | image/gif
    - 出力動画のアスペクト比が入力画像に合わせられる
    - 最低辺長: 300px（それ以下だと生成品質が著しく低下するため弾く）

  音声:
    - minimax/video-01 は音声入力に非対応
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


class ReplicateContentValidator:
    """Replicate (minimax/video-01) 向けコンテンツバリデーター。"""

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

        # ── MIME タイプ ─────────────────────────────────────────
        if (img.mime_type
                and img.mime_type in C.COMMON_IMAGE_ALLOWED_MIME
                and img.mime_type not in C.REPLICATE_IMAGE_ALLOWED_MIME):
            result.add_error(
                "image",
                f"Replicate: 非対応の画像形式です: {img.mime_type!r}  "
                f"（対応: {', '.join(sorted(C.REPLICATE_IMAGE_ALLOWED_MIME))}）",
            )

        # ── 最低辺長 ────────────────────────────────────────────
        for dim_name, dim_val in [("幅", img.width), ("高さ", img.height)]:
            if dim_val is not None and dim_val < C.REPLICATE_IMAGE_MIN_DIMENSION:
                result.add_error(
                    "image",
                    f"Replicate: 画像の{dim_name}が小さすぎます: {dim_val}px  "
                    f"（最小 {C.REPLICATE_IMAGE_MIN_DIMENSION}px 必要）",
                )

    # ── 音声 ─────────────────────────────────────────────────────

    def _mark_audio_unsupported(self, result: ContentValidationResult) -> None:
        """minimax/video-01 は音声入力に非対応。"""
        result.is_unsupported = True
        result.add_error(
            "audio",
            "Replicate (minimax/video-01): 音声入力は非対応です",
        )
