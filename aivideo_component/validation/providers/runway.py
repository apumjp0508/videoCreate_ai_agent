"""
Runway Gen-4 向けコンテンツバリデーター。

バリデーション順序:
  1. 共通チェック（validate_image_common / validate_audio_common）
  2. Runway 固有チェック

必須条件違反 → error  （is_valid = False）
推奨条件違反 → warning （is_valid はそのまま）

Runway 固有ルール:
  画像:
    - MIME: image/jpeg | image/png | image/webp （必須）
    - サイズ: URL 入力 16MB 以下（必須）、Base64 入力 5MB 以下（推奨 → warning）
    - 解像度: 640px 以上推奨（warning）、4K（3840px）以下推奨（warning）
  音声:
    - MIME: audio/mpeg | audio/wav | audio/flac | audio/mp4 | audio/aac （必須）
    - サイズ: 32MB 以下（必須）

注意:
  Runway は audio/flac・audio/aac を受け付けるが、
  共通チェック（COMMON_AUDIO_ALLOWED_MIME）ではこれらは対象外のためエラーになる。
  これは共通ルールの制約であり、Runway の制約ではない。
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


class RunwayContentValidator:
    """Runway Gen 向けコンテンツバリデーター。"""

    def validate(self, input: ContentValidationInput) -> ContentValidationResult:
        result = ContentValidationResult(is_valid=True)

        if input.image is not None:
            validate_image_common(input.image, result)
            self._validate_image(input, result)

        if input.audio is not None:
            validate_audio_common(input.audio, result)
            self._validate_audio(input, result)

        return result

    # ── 画像 ─────────────────────────────────────────────────────

    def _validate_image(
        self, input: ContentValidationInput, result: ContentValidationResult
    ) -> None:
        img = input.image
        if img is None:
            return

        # ── 必須: Runway 対応 MIME タイプ ──────────────────────
        # 共通チェックを通過した（= COMMON_IMAGE_ALLOWED_MIME 内の）MIME が
        # Runway では非対応のケースのみ追加エラーを出す。
        # 共通で弾かれた場合は共通エラーで十分なため重複させない。
        if (img.mime_type
                and img.mime_type in C.COMMON_IMAGE_ALLOWED_MIME
                and img.mime_type not in C.RUNWAY_IMAGE_ALLOWED_MIME):
            result.add_error(
                "image",
                f"Runway: 非対応の画像形式です: {img.mime_type!r}  "
                f"（Runway 対応: {', '.join(sorted(C.RUNWAY_IMAGE_ALLOWED_MIME))}）",
            )

        if img.file_size_bytes is not None:
            # ── 必須: URL 入力上限 16MB ─────────────────────────
            if img.file_size_bytes > C.RUNWAY_IMAGE_MAX_SIZE_URL_BYTES:
                result.add_error(
                    "image",
                    f"Runway: ファイルサイズが URL 入力の上限を超えています: "
                    f"{img.file_size_bytes / 1024 / 1024:.1f}MB  "
                    f"（Runway URL 入力上限: "
                    f"{C.RUNWAY_IMAGE_MAX_SIZE_URL_BYTES // (1024 * 1024)}MB）",
                )
            # ── 推奨: Base64 入力時は 5MB 以下 ──────────────────
            elif img.file_size_bytes > C.RUNWAY_IMAGE_MAX_SIZE_B64_BYTES:
                result.add_warning(
                    "image",
                    f"Runway: Base64 入力を使用する場合は "
                    f"{C.RUNWAY_IMAGE_MAX_SIZE_B64_BYTES // (1024 * 1024)}MB 以下推奨: "
                    f"現在 {img.file_size_bytes / 1024 / 1024:.1f}MB",
                )

        # ── 推奨: 解像度 640px 以上 / 4K 以下 ───────────────────
        for dim_name, dim_val in [("幅", img.width), ("高さ", img.height)]:
            if dim_val is None:
                continue
            if dim_val < C.RUNWAY_IMAGE_MIN_DIMENSION_RECOMMENDED:
                result.add_warning(
                    "image",
                    f"Runway: 画像の{dim_name}が推奨値を下回っています: "
                    f"{dim_val}px  "
                    f"（推奨: {C.RUNWAY_IMAGE_MIN_DIMENSION_RECOMMENDED}px 以上）",
                )
            elif dim_val > C.RUNWAY_IMAGE_MAX_DIMENSION_RECOMMENDED:
                result.add_warning(
                    "image",
                    f"Runway: 画像の{dim_name}が推奨上限（4K）を超えています: "
                    f"{dim_val}px  "
                    f"（推奨上限: {C.RUNWAY_IMAGE_MAX_DIMENSION_RECOMMENDED}px）",
                )

    # ── 音声 ─────────────────────────────────────────────────────

    def _validate_audio(
        self, input: ContentValidationInput, result: ContentValidationResult
    ) -> None:
        audio = input.audio
        if audio is None:
            return

        # ── 必須: Runway 対応 MIME タイプ ──────────────────────
        # RUNWAY_AUDIO_ALLOWED_MIME は COMMON_AUDIO_ALLOWED_MIME の上位互換なので、
        # 共通を通過した MIME は必ず Runway でも通過する。
        # 共通で弾かれた MIME には共通エラーが既に出ているため重複させない。
        # → 共通を通過したが Runway が非対応の形式のみエラーを追加する。
        if (audio.mime_type
                and audio.mime_type in C.COMMON_AUDIO_ALLOWED_MIME
                and audio.mime_type not in C.RUNWAY_AUDIO_ALLOWED_MIME):
            result.add_error(
                "audio",
                f"Runway: 非対応の音声形式です: {audio.mime_type!r}  "
                f"（Runway 対応: {', '.join(sorted(C.RUNWAY_AUDIO_ALLOWED_MIME))}）",
            )

        # ── 必須: ファイルサイズ 32MB 以下 ──────────────────────
        if audio.file_size_bytes is not None:
            if audio.file_size_bytes > C.RUNWAY_AUDIO_MAX_SIZE_BYTES:
                result.add_error(
                    "audio",
                    f"Runway: 音声ファイルサイズが上限を超えています: "
                    f"{audio.file_size_bytes / 1024 / 1024:.1f}MB  "
                    f"（Runway 上限: "
                    f"{C.RUNWAY_AUDIO_MAX_SIZE_BYTES // (1024 * 1024)}MB）",
                )
