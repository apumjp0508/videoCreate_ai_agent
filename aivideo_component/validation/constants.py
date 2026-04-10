"""
バリデーション条件の定数定義。

条件を変更する場合はこのファイルだけを修正すればよい。
プロバイダーごとのクラスや共通バリデーション関数はここの定数を参照する。
"""
from __future__ import annotations

_MB = 1024 * 1024  # bytes

# ════════════════════════════════════════════════════════════════
# 共通 — 画像
# ════════════════════════════════════════════════════════════════
#: 全プロバイダー共通で受け付ける画像 MIME タイプ
COMMON_IMAGE_ALLOWED_MIME: frozenset[str] = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
})
#: 共通 画像ファイルサイズ上限
COMMON_IMAGE_MAX_SIZE_BYTES: int = 10 * _MB          # 10 MB
#: 共通 画像の最小辺長 (px)
COMMON_IMAGE_MIN_DIMENSION: int = 300
#: 共通 画像の最大辺長 (px)
COMMON_IMAGE_MAX_DIMENSION: int = 4096
#: アスペクト比 w/h がこの値を超える（またはその逆数を下回る）と極端とみなす
#: 例: "1:10" → w/h = 0.1 → 1/10.0 < 閾値 → NG
COMMON_IMAGE_MAX_ASPECT_RATIO: float = 10.0

# ════════════════════════════════════════════════════════════════
# 共通 — 音声
# ════════════════════════════════════════════════════════════════
#: 全プロバイダー共通で受け付ける音声 MIME タイプ
COMMON_AUDIO_ALLOWED_MIME: frozenset[str] = frozenset({
    "audio/mpeg",
    "audio/wav",
    "audio/mp4",
})
#: 共通 音声の最大長 (秒)
COMMON_AUDIO_MAX_DURATION_SEC: float = 300.0
#: 共通 音声の最小サンプルレート (Hz)
COMMON_AUDIO_MIN_SAMPLE_RATE: int = 16_000
#: 共通 音声の最大サンプルレート (Hz)
COMMON_AUDIO_MAX_SAMPLE_RATE: int = 48_000
#: 共通 許容チャンネル数
COMMON_AUDIO_ALLOWED_CHANNELS: frozenset[int] = frozenset({1, 2})

# ════════════════════════════════════════════════════════════════
# Runway — 画像
# ════════════════════════════════════════════════════════════════
RUNWAY_IMAGE_ALLOWED_MIME: frozenset[str] = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
})
#: URL 入力時のファイルサイズ上限 (必須)
RUNWAY_IMAGE_MAX_SIZE_URL_BYTES: int = 16 * _MB
#: Base64 入力時のファイルサイズ上限 (推奨 — 超過で warning)
RUNWAY_IMAGE_MAX_SIZE_B64_BYTES: int = 5 * _MB
#: 推奨最小辺長 (px) — 下回ると warning
RUNWAY_IMAGE_MIN_DIMENSION_RECOMMENDED: int = 640
#: 推奨最大辺長 (px / 4K) — 超えると warning
RUNWAY_IMAGE_MAX_DIMENSION_RECOMMENDED: int = 3840

# ════════════════════════════════════════════════════════════════
# Runway — 音声
# ════════════════════════════════════════════════════════════════
#: Runway が受け付ける音声 MIME タイプ（共通より広い）
RUNWAY_AUDIO_ALLOWED_MIME: frozenset[str] = frozenset({
    "audio/mpeg",
    "audio/wav",
    "audio/flac",
    "audio/mp4",
    "audio/aac",
})
#: Runway 音声ファイルサイズ上限
RUNWAY_AUDIO_MAX_SIZE_BYTES: int = 32 * _MB

# ════════════════════════════════════════════════════════════════
# Kling — 画像
# ════════════════════════════════════════════════════════════════
KLING_IMAGE_ALLOWED_MIME: frozenset[str] = frozenset({
    "image/jpeg",
    "image/png",
})
#: Kling 画像ファイルサイズ上限 (必須)
KLING_IMAGE_MAX_SIZE_BYTES: int = 10 * _MB
#: Kling 画像の最小辺長 (px) — 必須
KLING_IMAGE_MIN_DIMENSION: int = 300

#: Kling が出力対応しているアスペクト比
#: 将来、出力設定との照合が必要になった場合はここを参照する
KLING_SUPPORTED_ASPECT_RATIOS: frozenset[str] = frozenset({
    "16:9",
    "9:16",
    "1:1",
    "4:3",
    "3:4",
})

# ════════════════════════════════════════════════════════════════
# Pika — 画像  (URL 入力前提 / 出力は 720p〜1080p に変換)
# ════════════════════════════════════════════════════════════════
PIKA_IMAGE_ALLOWED_MIME: frozenset[str] = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/avif",
})
#: 入力素材として不適切なケースを弾く最低辺長 (px)
PIKA_IMAGE_MIN_DIMENSION: int = 300

# ════════════════════════════════════════════════════════════════
# Replicate (minimax/video-01) — 画像
# first_frame_image として使用。URL 入力のみ対応。
# 出力動画のアスペクト比は入力画像に合わせられる。
# ════════════════════════════════════════════════════════════════
REPLICATE_IMAGE_ALLOWED_MIME: frozenset[str] = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
})
#: 入力素材として不適切なケースを弾く最低辺長 (px)
REPLICATE_IMAGE_MIN_DIMENSION: int = 300
