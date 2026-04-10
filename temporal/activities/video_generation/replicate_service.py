"""
Replicate API を使った動画生成サービス実装。

クラス構成:
  ReplicateVideoGenerationService   ─ Replicate API 共通ロジック（基底クラス）
  MinimaxVideoGenerationService     ─ minimax/video-01 用（テキスト + 画像 → 動画生成）
  ReplicateUpscaleService           ─ topazlabs/video-upscale 用（動画アップスケール）

Replicate API フロー:
  1. build_ai_request        ─ モデル固有の入力ペイロードを組み立てる（サブクラスで実装）
  2. submit_ai_request       ─ Prediction を作成して prediction_id を取得
  3. poll_generation_status  ─ Prediction のステータスを1回確認
  4. fetch_generated_video   ─ 完成動画 URL をそのまま返す

Replicate のステータス値:
  starting   → pending
  processing → processing
  succeeded  → completed
  failed     → failed
  canceled   → failed

API キー（REPLICATE_API_TOKEN）は credential_id 経由で DB から取得し、
Temporal ヒストリには含めない。

使い方（service_registry.py に登録する）:
    from temporal.activities.video_generation.replicate_service import (
        MinimaxVideoGenerationService,
    )
    APP_ENV_STAGING: lambda: MinimaxVideoGenerationService(),

モデル名・API エンドポイントの登録:
    VideoAiProvider.provider_key  = "replicate"
    VideoAiProvider.api_base_url  = "https://api.replicate.com/v1"
    VideoAiModel.model_name       = "minimax/video-01"  （または他の Replicate モデル名）
"""
from __future__ import annotations

import logging

from asgiref.sync import sync_to_async

from temporal.activities.video_generation.django_service import (
    AiConfigNotFoundError,
    DjangoVideoGenerationService,
)
from temporal.activities.video_generation.interfaces import (
    BuildAiRequestInput,
    BuildAiRequestOutput,
    FetchGeneratedVideoInput,
    FetchGeneratedVideoOutput,
    PollGenerationStatusInput,
    PollGenerationStatusOutput,
    SubmitAiRequestInput,
    SubmitAiRequestOutput,
)

logger = logging.getLogger(__name__)

# Replicate ステータス → 内部ステータスのマッピング
_STATUS_MAP: dict[str, str] = {
    "starting":   "pending",
    "processing": "processing",
    "succeeded":  "completed",
    "failed":     "failed",
    "canceled":   "failed",
}

_FAILED_STATUSES = frozenset({"failed", "canceled"})


# ─────────────────────────────────────────────────────────────
# 基底クラス: Replicate API 共通ロジック
# ─────────────────────────────────────────────────────────────

class ReplicateVideoGenerationService(DjangoVideoGenerationService):
    """
    Replicate AI を使った動画生成・処理サービスの基底クラス。

    DjangoVideoGenerationService を継承し、以下のメソッドを Replicate 固有に上書きする:
      - submit_ai_request       Prediction 作成・prediction_id の取得
      - poll_generation_status  Prediction ステータス確認
      - fetch_generated_video   完成動画 URL をそのまま返す

    build_ai_request はモデル固有のペイロードを組み立てるため、
    各サブクラスでオーバーライドすること。

    ai_request_payload の期待するフォーマット:
      {
          "model":       "<owner>/<model-name>",  # 例: "minimax/video-01"
          "model_input": { ... },                 # モデル固有の入力パラメータ
      }
    """

    # ── submit_ai_request ────────────────────────────────────────

    async def submit_ai_request(
        self, input: SubmitAiRequestInput
    ) -> SubmitAiRequestOutput:
        """
        Replicate Prediction を作成して prediction_id を取得する。

        replicate.Client を credential_id の API キーで初期化し、
        predictions.async_create() でジョブを開始する。
        """
        logger.info("[Replicate] submit_ai_request  job_id=%s", input.job_id)

        api_key     = await sync_to_async(self._get_api_key)(input.credential_id)
        model       = input.ai_request_payload["model"]
        model_input = input.ai_request_payload["model_input"]

        import replicate

        client     = replicate.Client(api_token=api_key)
        prediction = await client.predictions.async_create(
            model=model,
            input=model_input,
        )

        logger.info(
            "[Replicate] submit done  job_id=%s  prediction_id=%s  status=%s",
            input.job_id, prediction.id, prediction.status,
        )
        return SubmitAiRequestOutput(
            generation_id=prediction.id,
            initial_status=_STATUS_MAP.get(prediction.status, "pending"),
        )

    # ── poll_generation_status ───────────────────────────────────

    async def poll_generation_status(
        self, input: PollGenerationStatusInput
    ) -> PollGenerationStatusOutput:
        """
        Replicate Prediction のステータスを1回確認する。

        Workflow 側でこのメソッドを is_complete になるまでループ呼び出しする。
        """
        logger.info(
            "[Replicate] poll  job_id=%s  prediction_id=%s",
            input.job_id, input.generation_id,
        )

        api_key = await sync_to_async(self._get_api_key)(input.credential_id)

        import replicate

        client     = replicate.Client(api_token=api_key)
        prediction = await client.predictions.async_get(input.generation_id)

        raw_status  = prediction.status
        status      = _STATUS_MAP.get(raw_status, "pending")
        is_complete = status == "completed"
        is_failed   = raw_status in _FAILED_STATUSES

        video_url = ""
        if is_complete and prediction.output:
            output    = prediction.output
            video_url = output.url if hasattr(output, "url") else str(output)

        error_message = ""
        if is_failed:
            error_message = str(getattr(prediction, "error", "") or "")
            logger.warning(
                "[Replicate] failed  job_id=%s  prediction_id=%s  status=%s  error=%s",
                input.job_id, input.generation_id, raw_status, error_message,
            )
        else:
            logger.info(
                "[Replicate] poll result  job_id=%s  prediction_id=%s  status=%s  video_url=%s",
                input.job_id, input.generation_id, raw_status, video_url or "(none)",
            )

        return PollGenerationStatusOutput(
            generation_id=input.generation_id,
            status=status,
            is_complete=is_complete,
            is_failed=is_failed,
            video_url=video_url,
            error_message=error_message,
        )

    # ── fetch_generated_video ────────────────────────────────────

    async def fetch_generated_video(
        self, input: FetchGeneratedVideoInput
    ) -> FetchGeneratedVideoOutput:
        """
        poll_generation_status 完了時点で video_url が得られているため、
        追加の API 呼び出しは行わずそのまま返す。
        """
        logger.info(
            "[Replicate] fetch_generated_video  job_id=%s  video_url=%s",
            input.job_id, input.video_url,
        )
        return FetchGeneratedVideoOutput(
            video_url=input.video_url,
            video_metadata={},
        )

    # ── プライベートヘルパー ──────────────────────────────────────

    @staticmethod
    def _get_api_key(credential_id: int) -> str:
        """credential_id から REPLICATE_API_TOKEN を DB で取得する（同期）。"""
        from video_ai.models import UserVideoAiCredential

        try:
            credential = UserVideoAiCredential.objects.get(
                id=credential_id, is_active=True
            )
            return credential.api_key
        except UserVideoAiCredential.DoesNotExist:
            raise AiConfigNotFoundError(
                f"Replicate credential not found or inactive: credential_id={credential_id}"
            )


# ─────────────────────────────────────────────────────────────
# minimax/video-01  ─ テキスト + 画像 → 動画生成
# ─────────────────────────────────────────────────────────────

class MinimaxVideoGenerationService(ReplicateVideoGenerationService):
    """
    Replicate 上の minimax/video-01 を使った動画生成サービス。

    minimax/video-01 の入力仕様:
      prompt           : 動画生成プロンプト（必須）
      prompt_optimizer : プロンプト最適化フラグ（デフォルト True）
      first_frame_image: 最初のフレームに使用する画像 URL（省略可。指定すると動画の
                         アスペクト比がその画像に合わせられる）

    BuildAiRequestInput との対応:
      prompt_text      → prompt
      images[0].file_url → first_frame_image（画像が指定された場合のみ）
      config_params    → prompt_optimizer の上書き等に使用可能
    """

    async def build_ai_request(
        self, input: BuildAiRequestInput
    ) -> BuildAiRequestOutput:
        logger.info(
            "[Minimax] build_ai_request  job_id=%s  model=%s  has_image=%s",
            input.job_id, input.model_name, bool(input.images),
        )

        prompt_optimizer = bool(input.config_params.get("prompt_optimizer", True))

        model_input: dict = {
            "prompt":           input.prompt_text,
            "prompt_optimizer": prompt_optimizer,
        }

        # 画像が指定されていれば first_frame_image として追加
        # Django の ImageField.url は "/media/..." の相対パスを返すため
        # SITE_BASE_URL を付与して Replicate が要求する絶対 URI に変換する
        if input.images:
            first_image_url = _to_absolute_url(input.images[0].file_url)
            model_input["first_frame_image"] = first_image_url
            logger.info(
                "[Minimax] first_frame_image set  job_id=%s  url=%s",
                input.job_id, first_image_url,
            )

        payload = {
            "model":       input.model_name,   # "minimax/video-01"
            "model_input": model_input,
        }
        return BuildAiRequestOutput(ai_request_payload=payload)


# ─────────────────────────────────────────────────────────────
# topazlabs/video-upscale  ─ 動画アップスケール（4K化・FPS補完）
# ─────────────────────────────────────────────────────────────

class ReplicateUpscaleService(ReplicateVideoGenerationService):
    """
    Replicate 上の topazlabs/video-upscale を使った動画アップスケールサービス。

    topazlabs/video-upscale の入力仕様:
      video             : アップスケール対象の動画 URL（必須）
      target_fps        : 出力フレームレート（デフォルト 60）
      target_resolution : 出力解像度（デフォルト "4k"）

    BuildAiRequestInput との対応:
      images[0].file_url → video（動画ファイルを GeneratedImage として登録している場合）
      config_params      → target_fps / target_resolution の上書きに使用可能
    """

    async def build_ai_request(
        self, input: BuildAiRequestInput
    ) -> BuildAiRequestOutput:
        logger.info(
            "[Upscale] build_ai_request  job_id=%s  model=%s",
            input.job_id, input.model_name,
        )

        if not input.images:
            raise ValueError(
                f"[Upscale] build_ai_request: アップスケール対象の動画 URL が取得できません。"
                f"job_id={input.job_id}"
            )

        video_url         = _to_absolute_url(input.images[0].file_url)
        target_fps        = int(input.config_params.get("target_fps", 60))
        target_resolution = str(input.config_params.get("target_resolution", "4k"))

        model_input = {
            "video":             video_url,
            "target_fps":        target_fps,
            "target_resolution": target_resolution,
        }

        logger.info(
            "[Upscale] payload  job_id=%s  video_url=%s  fps=%d  resolution=%s",
            input.job_id, video_url, target_fps, target_resolution,
        )
        return BuildAiRequestOutput(ai_request_payload={
            "model":       input.model_name,   # "topazlabs/video-upscale"
            "model_input": model_input,
        })


# ─────────────────────────────────────────────────────────────
# モジュールレベルユーティリティ
# ─────────────────────────────────────────────────────────────

def _to_absolute_url(file_url: str) -> str:
    """
    Django の FileField.url が返す相対パス（例: /media/images/xxx.png）を
    Replicate が要求する絶対 URI（例: http://host/media/images/xxx.png）に変換する。

    すでに http:// / https:// で始まる場合はそのまま返す。
    SITE_BASE_URL は settings から取得し、デフォルトは http://localhost:8000。
    """
    if file_url.startswith(("http://", "https://")):
        return file_url

    from django.conf import settings
    base = getattr(settings, "SITE_BASE_URL", "http://localhost:8000").rstrip("/")
    return base + file_url
