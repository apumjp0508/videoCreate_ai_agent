"""
Kling 用コンテンツバリデーター。

現在は全項目を通過させるスタブ実装。
本実装時は Kling の制約に合わせて add_error / add_warning を追加する。

Kling の実際の制約（参考、本実装時に確認すること）:
  画像: JPEG / PNG, 最大 10MB, 推奨解像度 720px 以上, アスペクト比 16:9 / 9:16 / 1:1
  音声: Kling は音声入力（BGM）対応あり、MP3 / WAV
  スクリプト（テキストプロンプト）: 最大 2500 文字
"""
from aivideo_component.validation.protocol import (
    ContentValidationInput,
    ContentValidationResult,
)


class KlingContentValidator:
    """Kling 向けコンテンツバリデーター。"""

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
        #   - width >= 720 または height >= 720 であること（推奨解像度）
        #   - aspect_ratio が "16:9" | "9:16" | "1:1" であること
        pass

    def _validate_audio(self, input: ContentValidationInput, result: ContentValidationResult) -> None:
        # TODO: 本実装では以下を検証する
        #   - mime_type が "audio/mpeg" | "audio/wav" であること
        #   - duration_sec が制限内であること
        pass

    def _validate_script(self, input: ContentValidationInput, result: ContentValidationResult) -> None:
        # TODO: 本実装では以下を検証する
        #   - スクリプトが 2500 文字以内であること
        pass
