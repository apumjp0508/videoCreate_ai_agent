"""
Runway Gen-4 API を使った動画生成サービス実装。

Runway Image-to-Video API フロー:
  1. build_ai_request       ─ RunwayRequestBuilder（registry 経由）でペイロード組み立て
  2. submit_ai_request      ─ POST /v1/image_to_video でタスク開始・task_id 取得
  3. poll_generation_status ─ GET /v1/tasks/{task_id} でステータスをポーリング
  4. fetch_generated_video  ─ ポーリング完了時の video_url をそのまま返す

API キー取得の方針:
  APP_ENV=staging → 環境変数 RUNWAY_API_KEY から取得（.env に記載）
  APP_ENV=local   → UserVideoAiCredential.api_key を DB から取得

これにより staging では DB に API キーを登録しなくても動作する。

使い方（service_registry.py に登録する）:
    from temporal.activities.video_generation.runway_service import RunwayVideoGenerationService
    APP_ENV_STAGING: lambda: RunwayVideoGenerationService(),
"""
from __future__ import annotations

import logging
import os

import httpx
from asgiref.sync import sync_to_async

from temporal.activities.video_generation.django_service import (
    AiConfigNotFoundError,
    DjangoVideoGenerationService,
)
from temporal.activities.video_generation.interfaces import (
    FetchGeneratedVideoInput,
    FetchGeneratedVideoOutput,
    PollGenerationStatusInput,
    PollGenerationStatusOutput,
    SubmitAiRequestInput,
    SubmitAiRequestOutput,
)

logger = logging.getLogger(__name__)

# Runway API バージョンヘッダー
_RUNWAY_API_VERSION = "2024-11-06"

# Runway タスクステータス → 内部ステータスのマッピング
_STATUS_MAP: dict[str, str] = {
    "PENDING":   "pending",
    "RUNNING":   "processing",
    "SUCCEEDED": "completed",
    "FAILED":    "failed",
    "THROTTLED": "pending",   # 再試行待ちは pending 扱い
    "CANCELLED": "failed",
}

_FAILED_STATUSES = frozenset({"FAILED", "CANCELLED"})

_REQUEST_TIMEOUT = 30.0


class RunwayVideoGenerationService(DjangoVideoGenerationService):
    """
    Runway Gen-4 を使った動画生成サービス。

    DjangoVideoGenerationService を継承し、以下のメソッドを Runway 固有に上書きする:
      - submit_ai_request       POST /v1/image_to_video でタスク開始
      - poll_generation_status  GET /v1/tasks/{task_id} でステータス確認
      - fetch_generated_video   ポーリング済み video_url をそのまま返す

    build_ai_request は親クラス（DjangoVideoGenerationService）が
    request_builder/registry.py 経由で RunwayRequestBuilder を呼ぶため、
    このクラスでのオーバーライドは不要。

    DB 操作（fetch_materials / fetch_ai_config / fetch_request_definition /
    save_generated_video）は親クラスの実装をそのまま使う。
    """

    # ── submit_ai_request ────────────────────────────────────────

    async def submit_ai_request(
        self, input: SubmitAiRequestInput
    ) -> SubmitAiRequestOutput:
        """
        Runway Image-to-Video タスクを開始して task_id を取得する。

        POST {api_endpoint}/image_to_video
        Body: RunwayRequestBuilder が組み立てた ai_request_payload
              （provider / model キーは除いて送信する）
        """
        logger.info("[Runway] submit_ai_request  job_id=%s", input.job_id)

        api_key = await sync_to_async(self._get_api_key)(input.credential_id)
        url = _build_url(input.api_endpoint, "/image_to_video")

        # ai_request_payload から Runway API に不要なキーを除去し、
        # promptImage の相対 URL を絶対 URL に変換する
        body = {
            k: v for k, v in input.ai_request_payload.items()
            if k not in ("provider",)
        }
        if "promptImage" in body:
            body["promptImage"] = _to_absolute_url(body["promptImage"])

        logger.info("[Runway] submit body  job_id=%s  body=%s", input.job_id, body)

        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
            response = await client.post(
                url,
                headers=_auth_headers(api_key),
                json=body,
            )

        _raise_for_runway_error(response, "submit_ai_request", input.job_id)

        data = response.json()
        task_id = data["id"]
        initial_status = _STATUS_MAP.get(data.get("status", "PENDING"), "pending")

        logger.info(
            "[Runway] submit done  job_id=%s  task_id=%s  status=%s",
            input.job_id, task_id, initial_status,
        )
        return SubmitAiRequestOutput(
            generation_id=task_id,
            initial_status=initial_status,
        )

    # ── poll_generation_status ───────────────────────────────────

    async def poll_generation_status(
        self, input: PollGenerationStatusInput
    ) -> PollGenerationStatusOutput:
        """
        Runway タスクのステータスを1回確認する。

        GET {api_endpoint}/tasks/{task_id}

        Runway のステータス値:
          PENDING   → pending    （生成待ち）
          RUNNING   → processing （生成中）
          SUCCEEDED → completed  （完了）
          FAILED    → failed     （失敗）
          THROTTLED → pending    （レート制限・再試行待ち）
          CANCELLED → failed     （キャンセル）
        """
        logger.info(
            "[Runway] poll  job_id=%s  task_id=%s",
            input.job_id, input.generation_id,
        )

        api_key = await sync_to_async(self._get_api_key)(input.credential_id)
        url = _build_url(input.api_endpoint, f"/tasks/{input.generation_id}")

        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
            response = await client.get(url, headers=_auth_headers(api_key))

        _raise_for_runway_error(response, "poll_generation_status", input.job_id)

        data = response.json()
        raw_status  = data.get("status", "PENDING")
        status      = _STATUS_MAP.get(raw_status, "pending")
        is_complete = status == "completed"
        is_failed   = raw_status in _FAILED_STATUSES

        video_url = ""
        if is_complete:
            output = data.get("output") or []
            video_url = output[0] if output else ""

        error_message = ""
        if is_failed:
            error_message = str(data.get("failure", "") or data.get("failureCode", ""))
            logger.warning(
                "[Runway] failed  job_id=%s  task_id=%s  status=%s  error=%s",
                input.job_id, input.generation_id, raw_status, error_message,
            )
        else:
            logger.info(
                "[Runway] poll result  job_id=%s  task_id=%s  status=%s  video_url=%s",
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
            "[Runway] fetch_generated_video  job_id=%s  video_url=%s",
            input.job_id, input.video_url,
        )
        return FetchGeneratedVideoOutput(
            video_url=input.video_url,
            video_metadata={},
        )

    # ── API キー取得 ─────────────────────────────────────────────

    @staticmethod
    def _get_api_key(credential_id: int) -> str:
        """
        API キーを取得する。

        APP_ENV=staging : 環境変数 RUNWAY_API_KEY から取得（.env に記載）
        APP_ENV=local   : UserVideoAiCredential.api_key を DB から取得

        Raises:
            ValueError:          staging 環境で RUNWAY_API_KEY が未設定
            AiConfigNotFoundError: local 環境で credential が見つからない
        """
        app_env = os.environ.get("APP_ENV", "local").strip().lower()

        if app_env == "staging":
            api_key = os.environ.get("RUNWAY_API_KEY", "").strip()
            if not api_key:
                raise ValueError(
                    "RUNWAY_API_KEY が環境変数に設定されていません。"
                    "environment/staging/.env に RUNWAY_API_KEY=<your_key> を追加してください。"
                )
            logger.debug("[Runway] API キーを環境変数 RUNWAY_API_KEY から取得しました")
            return api_key

        # local: DB から取得
        from video_ai.models import UserVideoAiCredential

        try:
            credential = UserVideoAiCredential.objects.get(
                id=credential_id, is_active=True
            )
            logger.debug(
                "[Runway] API キーを DB から取得しました  credential_id=%d", credential_id
            )
            return credential.api_key
        except UserVideoAiCredential.DoesNotExist:
            raise AiConfigNotFoundError(
                f"Runway credential not found or inactive: credential_id={credential_id}"
            )


# ─────────────────────────────────────────────────────────────
# モジュールレベルユーティリティ
# ─────────────────────────────────────────────────────────────

def _build_url(base: str, path: str) -> str:
    """ベース URL とパスを結合して完全な URL を返す。"""
    base = (base or "https://api.runwayml.com/v1").rstrip("/")
    return base + path


def _auth_headers(api_key: str) -> dict:
    """Runway API 認証ヘッダーを返す。"""
    return {
        "Authorization":   f"Bearer {api_key}",
        "X-Runway-Version": _RUNWAY_API_VERSION,
        "Content-Type":    "application/json",
    }


def _to_absolute_url(file_url: str) -> str:
    """
    Django の FileField.url が返す相対パス（例: /media/images/xxx.png）を
    Runway が fetch できる絶対 URI に変換する。

    すでに http:// / https:// で始まる場合はそのまま返す。
    SITE_BASE_URL は settings から取得し、デフォルトは http://localhost:8000。
    """
    if file_url.startswith(("http://", "https://")):
        return file_url
    from django.conf import settings
    base = getattr(settings, "SITE_BASE_URL", "http://localhost:8000").rstrip("/")
    return base + file_url


def _raise_for_runway_error(
    response: httpx.Response,
    step: str,
    job_id: str,
) -> None:
    """
    Runway API のエラーレスポンスを解釈して例外を送出する。

    HTTP 4xx / 5xx のとき RuntimeError を送出する。
    """
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raw_body = response.text
        detail = raw_body
        try:
            detail = response.json()
        except Exception:
            pass
        logger.error(
            "[Runway] %s HTTP error  job_id=%s  status=%d  response=%s",
            step, job_id, response.status_code, detail,
        )
        raise RuntimeError(
            f"Runway API error at {step}  job_id={job_id}  "
            f"status={response.status_code}  detail={detail}"
        ) from exc
