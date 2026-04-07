"""
Kling 向けコンテンツバリデーター。

バリデーション順序:
  1. 共通チェック（validate_image_common / validate_audio_common）
  2. Kling 固有チェック

Kling 固有ルール:
  画像:
    - MIME: image/jpeg | image/png のみ（必須 — webp 不可）
    - サイズ: 10MB 以下（必須）
    - 解像度: 300px 以上（必須）
    - アスペクト比: Kling 対応値と一致（必須）

  音声:
    - API の直接入力仕様が未確定のため unsupported として扱う
    - 将来、仕様が確定した場合は _validate_audio を実装すること

アスペクト比の将来拡張:
  現時点では画像自身の aspect_ratio を基に判定する。
  将来、出力設定との照合が必要になった場合は
  ContentValidationInput に期待アスペクト比を渡す仕組みを追加すること。
  （例: ContentValidationInput.extra: dict に "expected_aspect_ratio" を格納）
  判定ロジックは _validate_image_aspect_ratio に集約してあるため変更箇所は最小限になる。
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


class KlingContentValidator:
    """Kling 向けコンテンツバリデーター。"""

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
        # KLING_IMAGE_ALLOWED_MIME は COMMON_IMAGE_ALLOWED_MIME の部分集合（webp を含まない）。
        # webp のように「共通は通過するが Kling では非対応」のケースのみ追加エラーを出す。
        # 共通で既に弾かれた MIME（bmp など）は共通エラーで十分なため重複させない。
        if (img.mime_type
                and img.mime_type in C.COMMON_IMAGE_ALLOWED_MIME
                and img.mime_type not in C.KLING_IMAGE_ALLOWED_MIME):
            result.add_error(
                "image",
                f"Kling: 非対応の画像形式です: {img.mime_type!r}  "
                f"（Kling 対応: {', '.join(sorted(C.KLING_IMAGE_ALLOWED_MIME))}）",
            )

        # ── 必須: ファイルサイズ 10MB 以下 ──────────────────────
        if img.file_size_bytes is not None:
            if img.file_size_bytes > C.KLING_IMAGE_MAX_SIZE_BYTES:
                result.add_error(
                    "image",
                    f"Kling: ファイルサイズが上限を超えています: "
                    f"{img.file_size_bytes / 1024 / 1024:.1f}MB  "
                    f"（Kling 上限: {C.KLING_IMAGE_MAX_SIZE_BYTES // (1024 * 1024)}MB）",
                )

        # ── 必須: 解像度 300px 以上 ──────────────────────────────
        for dim_name, dim_val in [("幅", img.width), ("高さ", img.height)]:
            if dim_val is not None and dim_val < C.KLING_IMAGE_MIN_DIMENSION:
                result.add_error(
                    "image",
                    f"Kling: 画像の{dim_name}が最小値を下回っています: "
                    f"{dim_val}px  "
                    f"（Kling 最小: {C.KLING_IMAGE_MIN_DIMENSION}px）",
                )

        # ── 必須: アスペクト比 ──────────────────────────────────
        self._validate_image_aspect_ratio(img.aspect_ratio, result)

    def _validate_image_aspect_ratio(
        self, aspect_ratio: str, result: ContentValidationResult
    ) -> None:
        """
        アスペクト比の検証。

        現時点: 画像自身の aspect_ratio が Kling 対応値かチェックする。
        将来の拡張: 出力設定の期待アスペクト比と比較する場合は
                   引数に expected_aspect_ratio: str | None を追加して比較ロジックを追記すること。
        """
        if not aspect_ratio:
            # aspect_ratio 未設定は警告止まり（アップロード時に設定されていない場合を考慮）
            result.add_warning(
                "image",
                "Kling: アスペクト比が未設定です。生成時に想定外のトリミングが発生する可能性があります。",
            )
            return

        if aspect_ratio not in C.KLING_SUPPORTED_ASPECT_RATIOS:
            result.add_error(
                "image",
                f"Kling: アスペクト比が対応値外です: {aspect_ratio!r}  "
                f"（Kling 対応: {', '.join(sorted(C.KLING_SUPPORTED_ASPECT_RATIOS))}）",
            )

    # ── 音声 ─────────────────────────────────────────────────────

    def _mark_audio_unsupported(self, result: ContentValidationResult) -> None:
        """Kling は音声の直接入力が未確定のため unsupported として扱う。"""
        result.is_unsupported = True
        result.add_error(
            "audio",
            "Kling: 音声の直接入力は現時点では未対応です  "
            "（API 仕様確定後に実装予定）",
        )
