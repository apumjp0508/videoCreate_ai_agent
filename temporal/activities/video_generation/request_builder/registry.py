"""
provider_key → AiRequestBuilder のルーティングレジストリ。

バリデーション層の registry.py と同じパターンで構成:
  - RequestConfigRepository : DB から ProviderRequestConfig を取得（ORM に触れる唯一の場所）
  - _BUILDER_MAP            : provider_key → ビルダーインスタンスの静的マッピング
  - get_builder()           : 外部から呼ぶ唯一の窓口

新しいプロバイダーを追加するときは:
  1. providers/<provider>.py に AiRequestBuilderProtocol 準拠クラスを作成
  2. _BUILDER_MAP に { '<provider_key>': XxxRequestBuilder() } を追加
  コードの変更はここだけ。
"""
from __future__ import annotations

from temporal.activities.video_generation.request_builder.protocol import (
    AiRequestBuilderProtocol,
    ProviderRequestConfig,
)
from temporal.activities.video_generation.request_builder.providers.runway import (
    RunwayRequestBuilder,
)


# ── provider_key → ビルダーのマッピング ──────────────────────────
# forms.py の AI_PROVIDERS の id と一致させること
_BUILDER_MAP: dict[str, AiRequestBuilderProtocol] = {
    'runway': RunwayRequestBuilder(),
}


# ─────────────────────────────────────────────────────────────
# 例外
# ─────────────────────────────────────────────────────────────

class RequestBuilderNotFoundError(ValueError):
    """_BUILDER_MAP に登録されていない provider_key が指定された場合。"""


class RequestConfigNotFoundError(Exception):
    """DB に対応するプロバイダーレコードが存在しない場合。"""


# ─────────────────────────────────────────────────────────────
# DB 取得層（ここだけ Django ORM に触れる）
# ─────────────────────────────────────────────────────────────

class RequestConfigRepository:
    """
    VideoAiProvider / VideoAiProviderValidationConfig を DB から取得して
    ProviderRequestConfig dataclass に変換する。

    バリデーション層の ProviderConfigRepository と同じ責務・設計を持つ。
    """

    def get_by_provider_key(self, provider_key: str) -> ProviderRequestConfig:
        """
        provider_key ("runway" など) に対応する設定を返す。

        Raises:
            RequestConfigNotFoundError: DB にレコードがない場合
        """
        from video_ai.models import VideoAiProvider

        try:
            provider = (
                VideoAiProvider.objects
                .select_related('validation_config')
                .get(provider_key=provider_key, is_active=True)
            )
        except VideoAiProvider.DoesNotExist:
            raise RequestConfigNotFoundError(
                f"provider_key={provider_key!r} のプロバイダーが見つかりません"
            )
        return self._to_config(provider)

    @staticmethod
    def _to_config(provider) -> ProviderRequestConfig:
        cfg = getattr(provider, 'validation_config', None)
        return ProviderRequestConfig(
            provider_key=provider.provider_key,
            provider_name=provider.provider_name,
            api_base_url=provider.api_base_url,
            image_allowed_aspect_ratios=(
                cfg.image_allowed_aspect_ratios if cfg else None
            ),
            image_aspect_ratio_required=(
                cfg.image_aspect_ratio_required if cfg else False
            ),
        )


# ─────────────────────────────────────────────────────────────
# 公開 API
# ─────────────────────────────────────────────────────────────

_repo = RequestConfigRepository()


def get_builder(
    provider_key: str,
) -> tuple[AiRequestBuilderProtocol, ProviderRequestConfig]:
    """
    provider_key に対応するビルダーと DB 設定を返す。

    Args:
        provider_key: "runway" | "pika" | "kling" など

    Returns:
        (ビルダーインスタンス, ProviderRequestConfig)

    Raises:
        RequestBuilderNotFoundError: _BUILDER_MAP に未登録の provider_key
        RequestConfigNotFoundError:  DB にプロバイダーが存在しない
    """
    if provider_key not in _BUILDER_MAP:
        raise RequestBuilderNotFoundError(
            f"provider_key={provider_key!r} に対応するビルダーが登録されていません。"
            f"登録済み: {list(_BUILDER_MAP)}"
        )
    config = _repo.get_by_provider_key(provider_key)
    return _BUILDER_MAP[provider_key], config
