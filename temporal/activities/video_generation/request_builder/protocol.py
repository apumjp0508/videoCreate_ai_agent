"""
AI リクエストビルダーの抽象インターフェースと設定 dataclass。

バリデーション層（aivideo_component/validation/service.py）と同じ設計思想:
  - ProviderRequestConfig : DB 由来の設定を Django ORM から切り離した in-memory 表現
  - AiRequestBuilderProtocol : 各プロバイダー実装が準拠する構造的部分型

新しいプロバイダーを追加するときは:
  1. providers/<provider>.py に AiRequestBuilderProtocol 準拠クラスを作成
  2. registry.py の _BUILDER_MAP に登録する
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from temporal.activities.video_generation.interfaces import (
    BuildAiRequestInput,
    BuildAiRequestOutput,
)


@dataclass
class ProviderRequestConfig:
    """
    DB（VideoAiProvider / VideoAiProviderValidationConfig）から取得した
    リクエスト組み立てに必要な設定の in-memory 表現。

    バリデーション層の ProviderValidationConfig と同じ役割を担い、
    ビルダー側が Django ORM を直接知らなくて済むように隔離する。
    """
    provider_key: str
    provider_name: str
    api_base_url: str

    # 画像: アスペクト比（ビルダーがプロバイダー固有のサイズ文字列に変換するために使用）
    # None = 制限なし / DB の image_allowed_aspect_ratios をそのまま保持
    image_allowed_aspect_ratios: list[str] | None = None
    image_aspect_ratio_required: bool = False

    # プロバイダー固有の追加設定（DB の extra カラムや将来の拡張用）
    extra: dict = field(default_factory=dict)


class AiRequestBuilderProtocol(Protocol):
    """
    プロバイダー固有の AI API リクエストペイロードを組み立てる契約。

    継承は不要（構造的部分型）。
    build() が返す BuildAiRequestOutput.ai_request_payload は
    submit_ai_request Activity がそのまま AI API に送信する。
    """

    def build(
        self,
        input: BuildAiRequestInput,
        config: ProviderRequestConfig,
    ) -> BuildAiRequestOutput:
        """
        Args:
            input:  Workflow から渡されたリクエスト組み立て用入力
                    （プロンプト・素材・モデル名・動画長など）
            config: DB から取得したプロバイダー設定

        Returns:
            BuildAiRequestOutput: ai_request_payload にプロバイダー固有の
                                  リクエスト本体が入った出力
        """
        ...
