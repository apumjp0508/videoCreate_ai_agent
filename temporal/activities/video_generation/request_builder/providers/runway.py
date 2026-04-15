"""
Runway Gen-3 / Gen-4 AI リクエストビルダー。

Runway Image-to-Video API 仕様:
  POST /v1/image_to_video
  Headers:
    Authorization: Bearer <api_key>
    X-Runway-Version: 2024-11-06
    Content-Type: application/json
  Body (JSON):
    {
      "model":       "gen3a_turbo" | "gen4_turbo",
      "promptImage": "<image_url>",   # 参照画像（URL）
      "promptText":  "...",           # テキストプロンプト
      "duration":    5 | 10,          # 動画長（秒）
      "ratio":       "1280:768"       # 解像度比
    }

  レスポンス (202 Accepted):
    { "id": "<task_id>" }

  ポーリング:
    GET /v1/tasks/<task_id>
    → { "status": "PENDING"|"RUNNING"|"SUCCEEDED"|"FAILED", "output": ["<video_url>"] }

参考: https://docs.runwayml.com/
"""
from __future__ import annotations

import logging

from temporal.activities.video_generation.interfaces import (
    BuildAiRequestInput,
    BuildAiRequestOutput,
    ImageMaterial,
)
from temporal.activities.video_generation.request_builder.protocol import (
    AiRequestBuilderProtocol,  # noqa: F401 — Protocol 準拠の明示用
    ProviderRequestConfig,
)

logger = logging.getLogger(__name__)

# 使用するモデルを固定
_MODEL = "gen4_turbo"

# ── アスペクト比 → Runway ratio 文字列マッピング ──────────────
# Runway が受け付ける ratio は固定値のみ
_ASPECT_TO_RATIO: dict[str, str] = {
    "16:9":  "1280:720",
    "9:16":  "720:1280",
    "1:1":   "960:960",
    "4:3":   "1104:832",
    "3:4":   "832:1104",
    "21:9":  "1584:672",
}
_DEFAULT_RATIO = "1280:720"  # フォールバック (16:9)

# Runway がサポートする動画長（秒）
_SUPPORTED_DURATIONS = (5, 10)


class RunwayRequestBuilder:
    """
    Runway Gen-3 / Gen-4 向けリクエストペイロードを組み立てる。

    build() が返す ai_request_payload の構造:
      {
        "provider":    "runway",
        "model":       "<model_name>",
        "promptText":  "<text_prompt>",
        "promptImage": "<image_url>",  # 画像なしの場合は含まない
        "duration":    5 | 10,
        "ratio":       "<WxH>",
      }

    submit_ai_request（Runway 固有の送信実装）はこのペイロードをそのまま
    Runway API に転送する。
    """

    def build(
        self,
        input: BuildAiRequestInput,
        config: ProviderRequestConfig,
    ) -> BuildAiRequestOutput:
        logger.info(
            "RunwayRequestBuilder.build  job_id=%s  model=%s  images=%d  duration=%ds",
            input.job_id, _MODEL, len(input.images), input.video_length_sec,
        )

        duration    = _nearest_supported_duration(input.video_length_sec)
        ratio       = _resolve_ratio(input.images, config)
        prompt_image = _resolve_prompt_image(input.images)

        payload: dict = {
            "provider":   "runway",
            "model":      _MODEL,
            "promptText": input.prompt_text,
            "duration":   duration,
            "ratio":      ratio,
        }
        if prompt_image:
            payload["promptImage"] = prompt_image

        logger.info(
            "RunwayRequestBuilder.build done  "
            "job_id=%s  ratio=%s  duration=%d  has_image=%s",
            input.job_id, ratio, duration, bool(prompt_image),
        )
        return BuildAiRequestOutput(ai_request_payload=payload)


# ─────────────────────────────────────────────────────────────
# モジュールレベルヘルパー（テスト・再利用しやすいよう独立させる）
# ─────────────────────────────────────────────────────────────

def _nearest_supported_duration(video_length_sec: int) -> int:
    """
    Runway がサポートする動画長（5 秒 or 10 秒）の中から
    最も近い値を返す。

    Examples:
        1 → 5, 5 → 5, 7 → 5, 8 → 10, 10 → 10, 30 → 10
    """
    return min(_SUPPORTED_DURATIONS, key=lambda d: abs(d - video_length_sec))


def _resolve_ratio(
    images: list[ImageMaterial],
    config: ProviderRequestConfig,
) -> str:
    """
    素材画像のアスペクト比から Runway の ratio 文字列を決定する。

    優先順位:
      1. images[0].aspect_ratio が _ASPECT_TO_RATIO に存在する → 変換して使用
      2. マッピングにない値 → 警告ログ出力後にデフォルト (16:9) へフォールバック
      3. 画像なし → デフォルト (16:9)
    """
    if not images:
        return _DEFAULT_RATIO

    aspect_ratio = images[0].aspect_ratio
    if not aspect_ratio:
        return _DEFAULT_RATIO

    ratio = _ASPECT_TO_RATIO.get(aspect_ratio)
    if ratio:
        return ratio

    logger.warning(
        "RunwayRequestBuilder: 未対応のアスペクト比 %r → デフォルト %s にフォールバック",
        aspect_ratio, _DEFAULT_RATIO,
    )
    return _DEFAULT_RATIO


def _resolve_prompt_image(images: list[ImageMaterial]) -> str:
    """
    Runway は参照画像を 1 枚受け付ける。
    複数渡された場合は最初の 1 枚を使用する。
    画像なしの場合は空文字列を返す（Text-to-Video モード）。
    """
    return images[0].file_url if images else ""
