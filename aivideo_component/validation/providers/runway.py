"""
Runway 用コンテンツバリデーター。

現在は全項目を通過させるスタブ実装。
本実装時は Runway の制約に合わせて add_error / add_warning を追加する。

Runway の実際の制約（参考、本実装時に確認すること）:
  画像: JPEG / PNG / WebP, 最大 16MB, 推奨アスペクト比 16:9 / 9:16 / 1:1
  音声: MP3 / WAV, 最大 100MB
  スクリプト: 制限なし（Runway Gen は画像中心のためスクリプトは任意）
"""
from aivideo_component.validation.protocol import (
    ContentValidationInput,
    ContentValidationResult,
)


class RunwayContentValidator:
    """Runway Gen 向けコンテンツバリデーター。"""

    def validate(self, input: ContentValidationInput) -> ContentValidationResult:
        result = ContentValidationResult(is_valid=True)

        self._validate_image(input, result)
        self._validate_audio(input, result)
        self._validate_script(input, result)

        return result

    def _validate_image(self, input: ContentValidationInput, result: ContentValidationResult) -> None:
        # TODO: 本実装では以下を検証する
        #   - mime_type が "image/jpeg" | "image/png" | "image/webp" であること
        #   - file_size_bytes <= 16MB であること
        #   - aspect_ratio が Runway の推奨値であること
        pass

    def _validate_audio(self, input: ContentValidationInput, result: ContentValidationResult) -> None:
        # TODO: 本実装では以下を検証する
        #   - mime_type が "audio/mpeg" | "audio/wav" であること
        #   - file_size_bytes <= 100MB であること
        #   - duration_sec が制限内であること
        pass

    def _validate_script(self, input: ContentValidationInput, result: ContentValidationResult) -> None:
        # TODO: 本実装では以下を検証する
        #   - スクリプト文字数の上限チェック（あれば）
        pass
