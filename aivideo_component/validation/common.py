"""
全プロバイダー共通のバリデーション関数。

各プロバイダーバリデーターの先頭で呼び出し、
共通ルールを一元管理する。

設計:
  - Django モデルを知らない（ImageMeta / AudioMeta だけを受け取る）
  - result に errors / warnings を追加するだけで、result を返さない
  - parse_aspect_ratio はプロバイダーバリデーターからも再利用可能なよう公開する
"""
from __future__ import annotations

from aivideo_component.validation import constants as C
from aivideo_component.validation.protocol import (
    AudioMeta,
    ContentValidationResult,
    ImageMeta,
)


# ─────────────────────────────────────────────────────────────
# ユーティリティ（公開）
# ─────────────────────────────────────────────────────────────

def parse_aspect_ratio(aspect_ratio: str) -> float | None:
    """
    "16:9" → 16/9 ≈ 1.778 に変換する。
    パース不能な場合は None を返す。
    プロバイダーバリデーターから再利用できるよう公開している。
    """
    if not aspect_ratio or ":" not in aspect_ratio:
        return None
    parts = aspect_ratio.split(":", 1)
    try:
        w, h = float(parts[0]), float(parts[1])
        if h <= 0:
            return None
        return w / h
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────────
# 共通バリデーション関数
# ─────────────────────────────────────────────────────────────

def validate_image_common(image: ImageMeta, result: ContentValidationResult) -> None:
    """
    全プロバイダー共通の画像バリデーション。

    下記をすべて満たさない場合は result に error を追加する（is_valid = False になる）:
      - MIME タイプ: image/jpeg | image/png | image/webp
      - ファイルサイズ: 10MB 以下
      - 幅・高さ: 300px 以上 4096px 以下
      - アスペクト比: 極端でないこと（縦横比 1:10 以内）
    """
    # ── MIME タイプ ────────────────────────────────────────────
    if image.mime_type not in C.COMMON_IMAGE_ALLOWED_MIME:
        result.add_error(
            "image",
            f"非対応の画像形式です: {image.mime_type!r}  "
            f"（共通対応形式: {', '.join(sorted(C.COMMON_IMAGE_ALLOWED_MIME))}）",
        )

    # ── ファイルサイズ ─────────────────────────────────────────
    if image.file_size_bytes is not None:
        _max = C.COMMON_IMAGE_MAX_SIZE_BYTES
        if image.file_size_bytes > _max:
            result.add_error(
                "image",
                f"ファイルサイズが上限を超えています: "
                f"{image.file_size_bytes / 1024 / 1024:.1f}MB"
                f"（上限 {_max // (1024 * 1024)}MB）",
            )

    # ── 幅 ────────────────────────────────────────────────────
    if image.width is not None:
        if image.width < C.COMMON_IMAGE_MIN_DIMENSION:
            result.add_error(
                "image",
                f"画像の幅が小さすぎます: {image.width}px"
                f"（最小 {C.COMMON_IMAGE_MIN_DIMENSION}px）",
            )
        elif image.width > C.COMMON_IMAGE_MAX_DIMENSION:
            result.add_error(
                "image",
                f"画像の幅が大きすぎます: {image.width}px"
                f"（最大 {C.COMMON_IMAGE_MAX_DIMENSION}px）",
            )

    # ── 高さ ───────────────────────────────────────────────────
    if image.height is not None:
        if image.height < C.COMMON_IMAGE_MIN_DIMENSION:
            result.add_error(
                "image",
                f"画像の高さが小さすぎます: {image.height}px"
                f"（最小 {C.COMMON_IMAGE_MIN_DIMENSION}px）",
            )
        elif image.height > C.COMMON_IMAGE_MAX_DIMENSION:
            result.add_error(
                "image",
                f"画像の高さが大きすぎます: {image.height}px"
                f"（最大 {C.COMMON_IMAGE_MAX_DIMENSION}px）",
            )

    # ── アスペクト比 ───────────────────────────────────────────
    if image.aspect_ratio:
        ratio = parse_aspect_ratio(image.aspect_ratio)
        if ratio is None:
            result.add_error(
                "image",
                f"アスペクト比の形式が不正です: {image.aspect_ratio!r}  "
                f"（例: \"16:9\"）",
            )
        else:
            _max_r = C.COMMON_IMAGE_MAX_ASPECT_RATIO
            if ratio > _max_r or ratio < (1.0 / _max_r):
                result.add_error(
                    "image",
                    f"アスペクト比が極端すぎます: {image.aspect_ratio}  "
                    f"（縦横比が 1:{_max_r:.0f} を超えるものは全プロバイダーで使用不可）",
                )


def validate_audio_common(audio: AudioMeta, result: ContentValidationResult) -> None:
    """
    全プロバイダー共通の音声バリデーション。

    下記をすべて満たさない場合は result に error を追加する（is_valid = False になる）:
      - MIME タイプ: audio/mpeg | audio/wav | audio/mp4
      - 長さ: 0秒超 〜 300秒以下
      - サンプルレート: 16000〜48000 Hz
      - チャンネル数: 1 または 2
    """
    # ── MIME タイプ ────────────────────────────────────────────
    if audio.mime_type not in C.COMMON_AUDIO_ALLOWED_MIME:
        result.add_error(
            "audio",
            f"非対応の音声形式です: {audio.mime_type!r}  "
            f"（共通対応形式: {', '.join(sorted(C.COMMON_AUDIO_ALLOWED_MIME))}）",
        )

    # ── 長さ ───────────────────────────────────────────────────
    if audio.duration_sec is not None:
        if audio.duration_sec <= 0:
            result.add_error(
                "audio",
                f"音声の長さが不正です: {audio.duration_sec}秒  "
                f"（0より大きい値が必要です）",
            )
        elif audio.duration_sec > C.COMMON_AUDIO_MAX_DURATION_SEC:
            result.add_error(
                "audio",
                f"音声が長すぎます: {audio.duration_sec:.1f}秒  "
                f"（上限 {C.COMMON_AUDIO_MAX_DURATION_SEC:.0f}秒）",
            )

    # ── サンプルレート ─────────────────────────────────────────
    if audio.sample_rate is not None:
        _min = C.COMMON_AUDIO_MIN_SAMPLE_RATE
        _max = C.COMMON_AUDIO_MAX_SAMPLE_RATE
        if not (_min <= audio.sample_rate <= _max):
            result.add_error(
                "audio",
                f"サンプルレートが範囲外です: {audio.sample_rate} Hz  "
                f"（{_min}〜{_max} Hz）",
            )

    # ── チャンネル数 ───────────────────────────────────────────
    if audio.channels is not None:
        if audio.channels not in C.COMMON_AUDIO_ALLOWED_CHANNELS:
            result.add_error(
                "audio",
                f"非対応のチャンネル数です: {audio.channels}ch  "
                f"（対応: {sorted(C.COMMON_AUDIO_ALLOWED_CHANNELS)}）",
            )
