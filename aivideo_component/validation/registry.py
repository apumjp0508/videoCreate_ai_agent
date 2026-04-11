"""
バリデーター registry。

provider_key → DbDrivenContentValidator を返す唯一の窓口。
View はこの関数だけを呼べばよく、個々のバリデータークラスを知る必要はない。

新しいプロバイダーを追加するときは:
  1. DB の video_ai_providers にレコードを追加する
  2. video_ai_provider_validation_configs に条件レコードを追加する
  コードの変更は不要。
"""
from __future__ import annotations

from aivideo_component.validation.protocol import (
    ContentValidationInput,
    ContentValidationResult,
)
from aivideo_component.validation.service import (
    DbDrivenContentValidator,
    ProviderConfigNotFoundError,
    ProviderConfigRepository,
)

_repo = ProviderConfigRepository()


class UnknownProviderError(ValueError):
    """DB に設定が存在しない provider_key が指定された場合。"""


def get_validator(provider_key: str) -> DbDrivenContentValidator:
    """
    provider_key に対応する DB 駆動バリデーターを返す。

    Args:
        provider_key: "runway" | "pika" | "kling" など
    Returns:
        DbDrivenContentValidator インスタンス
    Raises:
        UnknownProviderError: DB に設定レコードが存在しない場合
    """
    try:
        config = _repo.get_by_provider_key(provider_key)
    except ProviderConfigNotFoundError as e:
        raise UnknownProviderError(str(e)) from e
    return DbDrivenContentValidator(config)


def validate_content(input: ContentValidationInput) -> ContentValidationResult:
    """
    入力の provider_key に対応するバリデーターを自動選択して実行する便利関数。
    View から直接呼ぶならこちらを使う。

    Args:
        input: バリデーション入力（provider_key を含む）
    Returns:
        ContentValidationResult
    Raises:
        UnknownProviderError: DB に設定レコードが存在しない場合
    """
    return get_validator(input.provider_key).validate(input)
