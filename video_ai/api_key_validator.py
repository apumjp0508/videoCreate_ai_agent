"""
AIプロバイダーAPIキー検証モジュール。

使い方:
    validator = get_validator("runway")
    result = validator.validate(api_key, provider.api_base_url)

新プロバイダー追加方法:
    1. BaseApiKeyValidator を継承したクラスを作成
    2. _VALIDATOR_REGISTRY に provider_key をキーとして登録
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ApiKeyValidationResult:
    """APIキー検証の結果。"""
    http_status: int          # HTTPステータスコード (接続失敗時は 0)
    validation_endpoint: str  # 実際にリクエストしたURL
    error_code: Optional[str] # プロバイダーが返したエラーコード (成功時は None)
    is_valid: bool


# ─────────────────────── 基底クラス ───────────────────────

class BaseApiKeyValidator(ABC):
    """全プロバイダー共通のインターフェース。"""

    REQUEST_TIMEOUT = 10  # 秒

    @abstractmethod
    def validate(self, api_key: str, base_url: str) -> ApiKeyValidationResult:
        """
        APIキーを検証する。

        Args:
            api_key:  検証対象のAPIキー
            base_url: VideoAiProvider.api_base_url

        Returns:
            ApiKeyValidationResult
        """

    # ── 共通ユーティリティ ──────────────────────────────────

    @staticmethod
    def _build_url(base_url: str, path: str) -> str:
        return base_url.rstrip("/") + "/" + path.lstrip("/")

    @staticmethod
    def _extract_error_code(body_bytes: bytes) -> Optional[str]:
        """レスポンスボディからエラーコードを抽出する。"""
        try:
            body = json.loads(body_bytes)
        except (ValueError, TypeError):
            return None

        # 主要なAPIが使うエラーコードフィールド名を順に試す
        for key in ("error", "code", "error_code", "errorCode", "status"):
            val = body.get(key)
            if val is None:
                continue
            # {"error": {"code": "..."}} のようなネスト構造にも対応
            if isinstance(val, dict):
                inner = val.get("code") or val.get("type") or val.get("message")
                if inner:
                    return str(inner)
            return str(val)

        return None

    def _get(
        self,
        url: str,
        headers: dict,
    ) -> ApiKeyValidationResult:
        """
        GET リクエストを送り ApiKeyValidationResult を返す汎用メソッド。
        接続エラーは is_valid=False, http_status=0 として扱う。
        """
        logger.info("API key validation request: GET %s", url)
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.REQUEST_TIMEOUT) as resp:
                status = resp.status
                resp.read()  # レスポンスボディを読み切って接続を安全にクローズ
                logger.info("API key validation response: status=%d  url=%s", status, url)
                return ApiKeyValidationResult(
                    http_status=status,
                    validation_endpoint=url,
                    error_code=None,
                    is_valid=True,
                )
        except urllib.error.HTTPError as exc:
            body_bytes = exc.read() if exc.fp else b""
            error_code = self._extract_error_code(body_bytes)
            logger.warning(
                "API key validation HTTP error: status=%d  url=%s  error_code=%s",
                exc.code, url, error_code,
            )
            return ApiKeyValidationResult(
                http_status=exc.code,
                validation_endpoint=url,
                error_code=error_code,
                is_valid=False,
            )
        except urllib.error.URLError as exc:
            logger.warning("API key validation URL error: url=%s  reason=%s", url, exc.reason)
            return ApiKeyValidationResult(
                http_status=0,
                validation_endpoint=url,
                error_code=str(exc.reason),
                is_valid=False,
            )
        except Exception as exc:
            logger.warning("API key validation unexpected error: url=%s  error=%s", url, exc)
            return ApiKeyValidationResult(
                http_status=0,
                validation_endpoint=url,
                error_code=str(exc),
                is_valid=False,
            )


# ─────────────────────── 汎用実装 ───────────────────────

class BearerTokenValidator(BaseApiKeyValidator):
    """
    Authorization: Bearer {key} で GET するだけの汎用バリデーター。
    多くのREST APIはこれで対応できる。
    """

    def __init__(self, path: str, extra_headers: Optional[dict] = None):
        self._path = path
        self._extra_headers = extra_headers or {}

    def validate(self, api_key: str, base_url: str) -> ApiKeyValidationResult:
        url = self._build_url(base_url, self._path)
        headers = {
            "Authorization": f"Bearer {api_key}",
            **self._extra_headers,
        }
        return self._get(url, headers)


# ─────────────────────── プロバイダー別実装 ───────────────────────

class RunwayApiKeyValidator(BearerTokenValidator):
    """
    Runway: GET /v1/organization
    必須ヘッダー: X-Runway-Version
    """

    VALIDATION_PATH = "/v1/organization"

    def __init__(self):
        super().__init__(
            path=self.VALIDATION_PATH,
            extra_headers={"X-Runway-Version": "2024-11-06"},
        )


class PikaApiKeyValidator(BearerTokenValidator):
    """
    Pika: GET /v1/credits (軽量な残高確認エンドポイント)
    """

    VALIDATION_PATH = "/v1/credits"

    def __init__(self):
        super().__init__(path=self.VALIDATION_PATH)


class KlingApiKeyValidator(BaseApiKeyValidator):
    """
    Kling: HMAC-SHA256 署名付きJWTで認証する。
    GET /v1/account/costs で検証する。

    Klingは api_key = "access_key:secret_key" の形式を想定。
    """

    VALIDATION_PATH = "/v1/account/costs"

    def validate(self, api_key: str, base_url: str) -> ApiKeyValidationResult:
        url = self._build_url(base_url, self.VALIDATION_PATH)
        token = self._build_jwt(api_key)
        if token is None:
            return ApiKeyValidationResult(
                http_status=0,
                validation_endpoint=url,
                error_code="invalid_api_key_format",
                is_valid=False,
            )
        headers = {"Authorization": f"Bearer {token}"}
        return self._get(url, headers)

    @staticmethod
    def _build_jwt(api_key: str) -> Optional[str]:
        """
        "access_key:secret_key" 形式のAPIキーからJWTを生成する。
        jwt パッケージが無い環境では None を返す。
        """
        try:
            import time
            import jwt as pyjwt

            if ":" not in api_key:
                return None
            access_key, secret_key = api_key.split(":", 1)
            payload = {
                "iss": access_key,
                "exp": int(time.time()) + 1800,
                "nbf": int(time.time()) - 5,
            }
            return pyjwt.encode(payload, secret_key, algorithm="HS256")
        except Exception as exc:
            logger.warning("Kling JWT generation failed: %s", exc)
            return None


class ReplicateApiKeyValidator(BaseApiKeyValidator):
    """
    Replicate: GET /models でモデル一覧を取得してトークンの有効性を検証する。
    api_base_url が "https://api.replicate.com/v1" のため、
    _build_url との結合後は "https://api.replicate.com/v1/models" になる。

    urllib では User-Agent "Python-urllib/x.x" が Replicate にブロックされ 403 になるため
    httpx を使用する。
    """

    VALIDATION_PATH = "/models"

    def validate(self, api_key: str, base_url: str) -> ApiKeyValidationResult:
        import httpx

        url = self._build_url(base_url, self.VALIDATION_PATH)
        logger.info("Replicate API key validation: GET %s", url)
        try:
            response = httpx.get(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=self.REQUEST_TIMEOUT,
                follow_redirects=True,
            )
            logger.info(
                "Replicate API key validation response: status=%d  url=%s",
                response.status_code, url,
            )
            if response.is_success:
                return ApiKeyValidationResult(
                    http_status=response.status_code,
                    validation_endpoint=url,
                    error_code=None,
                    is_valid=True,
                )
            error_code = self._extract_error_code(response.content)
            logger.warning(
                "Replicate API key validation failed: status=%d  error_code=%s",
                response.status_code, error_code,
            )
            return ApiKeyValidationResult(
                http_status=response.status_code,
                validation_endpoint=url,
                error_code=error_code,
                is_valid=False,
            )
        except Exception as exc:
            logger.warning("Replicate API key validation error: url=%s  error=%s", url, exc)
            return ApiKeyValidationResult(
                http_status=0,
                validation_endpoint=url,
                error_code=str(exc),
                is_valid=False,
            )


# ─────────────────────── レジストリ & ファクトリー ───────────────────────

_VALIDATOR_REGISTRY: dict[str, BaseApiKeyValidator] = {
    "runway":    RunwayApiKeyValidator(),
    "pika":      PikaApiKeyValidator(),
    "kling":     KlingApiKeyValidator(),
    "replicate": ReplicateApiKeyValidator(),
}


def get_validator(provider_key: str) -> BaseApiKeyValidator:
    """
    プロバイダーキーに対応するバリデーターを返す。

    新プロバイダーを追加する場合は _VALIDATOR_REGISTRY にエントリを追加するだけでよい。

    Raises:
        KeyError: 未登録のプロバイダーキーが指定された場合
    """
    validator = _VALIDATOR_REGISTRY.get(provider_key)
    if validator is None:
        raise KeyError(
            f"provider_key '{provider_key}' に対応するバリデーターが登録されていません。"
            f"登録済み: {list(_VALIDATOR_REGISTRY)}"
        )
    return validator


def validate_api_key(api_key: str, provider_key: str, base_url: str) -> ApiKeyValidationResult:
    """
    APIキーを検証して結果を返す便利関数。

    Args:
        api_key:      ユーザーが入力したAPIキー
        provider_key: VideoAiProvider.provider_key
        base_url:     VideoAiProvider.api_base_url

    Returns:
        ApiKeyValidationResult
    """
    validator = get_validator(provider_key)
    return validator.validate(api_key, base_url)
