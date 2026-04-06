"""
Pika 用コンテンツバリデーター。

現在は全項目を通過させるスタブ実装。
本実装時は Pika の制約に合わせて add_error / add_warning を追加する。

Pika の実際の制約（参考、本実装時に確認すること）:
  画像: JPEG / PNG, 最大 10MB, アスペクト比 16:9 / 9:16 / 1:1 など
  音声: Pika は音声入力対応が限定的（バージョンにより異なる）
  スクリプト（テキストプロンプト）: 最大 1000 文字程度
"""
from aivideo_component.validation.protocol import (
    ContentValidationInput,
    ContentValidationResult,
)


class PikaContentValidator:
    """Pika 向けコンテンツバリデーター。"""

    def validate(self, input: ContentValidationInput) -> ContentValidationResult:
        result = ContentValidationResult(is_valid=True)

        self._validate_image(input, result)
        self._validate_audio(input, result)
        self._validate_script(input, result)

        return result

    def _validate_image(self, input: ContentValidationInput, result: ContentValidationResult) -> None:
        # TODO: 本実装では以下を検証する
        #   - mime_type が "image/jpeg" | "image/png" であること
        #   - file_size_bytes <= 10MB であること
        #   - アスペクト比が Pika の対応値であること
        pass

    def _validate_audio(self, input: ContentValidationInput, result: ContentValidationResult) -> None:
        # TODO: 本実装では以下を検証する
        #   - Pika が音声入力に対応しているバージョンか確認
        #   - 対応している場合、対応フォーマットの確認
        pass

    def _validate_script(self, input: ContentValidationInput, result: ContentValidationResult) -> None:
        # TODO: 本実装では以下を検証する
        #   - スクリプトが 1000 文字以内であること
        pass
