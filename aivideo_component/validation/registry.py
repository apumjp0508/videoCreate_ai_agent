"""
バリデーター registry。

provider_key → ContentValidatorProtocol 準拠のバリデーターを返す唯一の窓口。
View はこの関数だけを呼べばよく、個々のバリデータークラスを知る必要はない。

新しいプロバイダーを追加するときは:
  1. providers/ に新しいバリデーターファイルを作る
  2. _REGISTRY にエントリを1行追加する
  それだけでよい。View / Workflow 側は変更不要。
"""
from __future__ import annotations

from aivideo_component.validation.protocol import (
    ContentValidationInput,
    ContentValidationResult,
    ContentValidatorProtocol,
)
from aivideo_component.validation.providers.kling import KlingContentValidator
from aivideo_component.validation.providers.pika import PikaContentValidator
from aivideo_component.validation.providers.runway import RunwayContentValidator

# ── プロバイダーキー → バリデーターのマッピング ─────────────────
# forms.py の AI_PROVIDERS の id と一致させること
_REGISTRY: dict[str, ContentValidatorProtocol] = {
    'runway': RunwayContentValidator(),
    'pika':   PikaContentValidator(),
    'kling':  KlingContentValidator(),
}


class UnknownProviderError(ValueError):
    """registry に未登録の provider_key が指定された場合。"""


def get_validator(provider_key: str) -> ContentValidatorProtocol:
    """
    provider_key に対応するバリデーターを返す。

    Args:
        provider_key: "runway" | "pika" | "kling" など
    Returns:
        ContentValidatorProtocol 準拠のバリデーターインスタンス
    Raises:
        UnknownProviderError: 登録されていない provider_key の場合
    """
    validator = _REGISTRY.get(provider_key)
    if validator is None:
        raise UnknownProviderError(
            f"バリデーターが登録されていません: provider_key={provider_key!r}  "
            f"登録済み={list(_REGISTRY.keys())}"
        )
    return validator


def validate_content(input: ContentValidationInput) -> ContentValidationResult:
    """
    入力の provider_key に対応するバリデーターを自動選択して実行する便利関数。
    View から直接呼ぶならこちらを使う。

    Args:
        input: バリデーション入力（provider_key を含む）
    Returns:
        ContentValidationResult
    Raises:
        UnknownProviderError: 未登録の provider_key の場合
    """
    return get_validator(input.provider_key).validate(input)
