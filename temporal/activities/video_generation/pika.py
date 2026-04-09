"""
Pika API を使った動画生成サービス実装。

Pika API 仕様:
  POST /v1/generate          ─ 動画生成ジョブを開始
  GET  /v1/generate/{job_id} ─ ステータスと生成済み video_url を取得

処理フロー:
  1. build_ai_request         ─ Pika 形式のリクエストペイロードを組み立てる
  2. submit_ai_request        ─ POST /v1/generate で生成ジョブを開始し job_id を取得
  3. poll_generation_status   ─ GET /v1/generate/{job_id} でステータスをポーリング
  4. fetch_generated_video    ─ ポーリング完了時の video_url をそのまま返す

API キーはすべて credential_id 経由で DB から取得し、Temporal ヒストリには含めない。

使い方（service_registry.py に登録する）:
    from temporal.activities.video_generation.pika import PikaVideoGenerationService
    # staging 環境に差し替え
    APP_ENV_STAGING: lambda: PikaVideoGenerationService(),
"""
from __future__ import annotations

import logging

import httpx
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

# Pika API のデフォルトベース URL
# VideoAiProvider.api_base_url にも同じ値を登録しておくこと
PIKA_API_BASE_URL = "https://api.pika.art"

# Pika API のタイムアウト設定
_REQUEST_TIMEOUT = 30.0


class PikaVideoGenerationService(DjangoVideoGenerationService):
    """
    Pika AI を使った動画生成サービス。

    DjangoVideoGenerationService を継承し、以下のメソッドを Pika 固有に上書きする:
      - build_ai_request        Pika 用ペイロードの組み立て
      - submit_ai_request       POST /v1/generate でジョブ開始
      - poll_generation_status  GET /v1/generate/{job_id} でステータス確認
      - fetch_generated_video   ポーリング済み video_url をそのまま返す

    DB 操作（fetch_materials / fetch_ai_config / fetch_request_definition /
    save_generated_video）は親クラスの実装をそのまま使う。
    """

    # ── build_ai_request ─────────────────────────────────────────

    async def build_ai_request(
        self, input: BuildAiRequestInput
    ) -> BuildAiRequestOutput:
        """
        Pika API 用のリクエストペイロードを組み立てる。

        Pika リクエスト仕様:
          prompt        : 動画生成プロンプト
          image         : 参照画像の URL（最初の1枚）
          image_prompt  : 画像の説明文
          duration      : 動画の長さ（秒）
          aspect_ratio  : アスペクト比（デフォルト 16:9）
        """
        logger.info(
            "[Pika] build_ai_request  job_id=%s  model=%s  duration=%d sec",
            input.job_id, input.model_name, input.video_length_sec,
        )

        # 最初の画像素材の URL と説明文を取得
        image_url: str = ""
        image_prompt: str = ""
        if input.images:
            first = input.images[0]
            image_url = first.file_url
            image_prompt = first.description

        # フォーマット設定からアスペクト比を取得（未指定なら 16:9）
        aspect_ratio = input.format_settings.get("aspect_ratio", "16:9")

        payload = {
            "prompt":       input.prompt_text,
            "image":        image_url,
            "image_prompt": image_prompt,
            "duration":     input.video_length_sec,
            "aspect_ratio": aspect_ratio,
        }
        logger.info(
            "[Pika] payload built  job_id=%s  image_url=%s  aspect_ratio=%s",
            input.job_id, image_url, aspect_ratio,
        )
        return BuildAiRequestOutput(ai_request_payload=payload)

    # ── submit_ai_request ────────────────────────────────────────

    async def submit_ai_request(
        self, input: SubmitAiRequestInput
    ) -> SubmitAiRequestOutput:
        """
        Pika API に動画生成リクエストを送信して job_id を取得する。

        POST {api_endpoint}/v1/generate
        Body: ai_request_payload（build_ai_request が組み立てたもの）
        """
        logger.info("[Pika] submit_ai_request  job_id=%s", input.job_id)

        api_key = await sync_to_async(self._get_api_key)(input.credential_id)
        url = _build_url(input.api_endpoint, "/v1/generate")

        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
            response = await client.post(
                url,
                headers=_auth_headers(api_key),
                json=input.ai_request_payload,
            )

        _raise_for_pika_error(response, "submit_ai_request", input.job_id)

        data = response.json()
        pika_job_id = data["id"]
        initial_status = data.get("status", "pending")

        logger.info(
            "[Pika] submit_ai_request done  job_id=%s  pika_job_id=%s  status=%s",
            input.job_id, pika_job_id, initial_status,
        )
        return SubmitAiRequestOutput(
            generation_id=pika_job_id,
            initial_status=initial_status,
        )

    # ── poll_generation_status ───────────────────────────────────

    async def poll_generation_status(
        self, input: PollGenerationStatusInput
    ) -> PollGenerationStatusOutput:
        """
        Pika API でジョブのステータスを1回確認する。

        GET {api_endpoint}/v1/generate/{generation_id}

        Pika のステータス値:
          pending    : 生成待ち
          processing : 生成中
          completed  : 完了（video_url あり）
          failed     : 失敗
        """
        logger.info(
            "[Pika] poll_generation_status  job_id=%s  pika_job_id=%s",
            input.job_id, input.generation_id,
        )

        api_key = await sync_to_async(self._get_api_key)(input.credential_id)
        url = _build_url(input.api_endpoint, f"/v1/generate/{input.generation_id}")

        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
            response = await client.get(url, headers=_auth_headers(api_key))

        _raise_for_pika_error(response, "poll_generation_status", input.job_id)

        data = response.json()
        status = data.get("status", "pending")
        is_complete = status == "completed"
        is_failed = status == "failed"
        video_url = data.get("video_url", "") if is_complete else ""

        if is_failed:
            error_detail = data.get("error", "")
            logger.warning(
                "[Pika] generation failed  job_id=%s  pika_job_id=%s  error=%s",
                input.job_id, input.generation_id, error_detail,
            )
        else:
            logger.info(
                "[Pika] poll result  job_id=%s  pika_job_id=%s  status=%s  video_url=%s",
                input.job_id, input.generation_id, status, video_url or "(none)",
            )

        return PollGenerationStatusOutput(
            generation_id=input.generation_id,
            status=status,
            is_complete=is_complete,
            is_failed=is_failed,
            video_url=video_url,
        )

    # ── fetch_generated_video ────────────────────────────────────

    async def fetch_generated_video(
        self, input: FetchGeneratedVideoInput
    ) -> FetchGeneratedVideoOutput:
        """
        Pika では poll_generation_status 完了時点で video_url が得られているため、
        このステップでは追加の API 呼び出しは行わずそのまま返す。
        """
        logger.info(
            "[Pika] fetch_generated_video  job_id=%s  video_url=%s",
            input.job_id, input.video_url,
        )
        return FetchGeneratedVideoOutput(
            video_url=input.video_url,
            video_metadata={},
        )

    # ── プライベートヘルパー ──────────────────────────────────────

    @staticmethod
    def _get_api_key(credential_id: int) -> str:
        """credential_id から API キーを DB で取得する（同期）。"""
        from video_ai.models import UserVideoAiCredential

        try:
            credential = UserVideoAiCredential.objects.get(
                id=credential_id, is_active=True
            )
            return credential.api_key
        except UserVideoAiCredential.DoesNotExist:
            raise AiConfigNotFoundError(
                f"Pika credential not found or inactive: credential_id={credential_id}"
            )


# ─────────────────────────────────────────────────────────────
# モジュールレベルユーティリティ
# ─────────────────────────────────────────────────────────────

def _build_url(base: str, path: str) -> str:
    """ベース URL とパスを結合して完全な URL を返す。"""
    base = base.rstrip("/") if base else PIKA_API_BASE_URL.rstrip("/")
    return base + path


def _auth_headers(api_key: str) -> dict:
    """Pika API 認証ヘッダーを返す。"""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }


def _raise_for_pika_error(
    response: httpx.Response,
    step: str,
    job_id: str,
) -> None:
    """
    Pika API のエラーレスポンスを解釈して例外を送出する。

    Pika はエラー時に {"error": "..."} を返すことがある。
    HTTP ステータスが 4xx / 5xx の場合は httpx.HTTPStatusError を送出。
    """
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = ""
        try:
            body = response.json().get("error", response.text)
        except Exception:
            body = response.text
        logger.error(
            "[Pika] %s HTTP error  job_id=%s  status=%d  body=%s",
            step, job_id, response.status_code, body,
        )
        raise RuntimeError(
            f"Pika API error at {step}  job_id={job_id}  "
            f"status={response.status_code}  detail={body}"
        ) from exc
