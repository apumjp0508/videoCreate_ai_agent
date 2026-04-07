"""
ContentValidationService: DB保存済みメタ情報を使ったバリデーションサービス。

責務:
  - GeneratedImage / GeneratedAudio モデルインスタンス → ImageMeta / AudioMeta 変換
    （実ファイルは読み込まない）
  - registry 経由でプロバイダーバリデーターを呼び出す
  - 結果の provider_key / asset_type を設定する
  - 任意で結果を既存の validation_status / validation_message に保存する

使い方::

    from aivideo_component.validation.service import ContentValidationService

    service = ContentValidationService()

    # 1. 結果を取得するだけ（DB 保存なし）
    result = service.validate_image(image, "runway")
    result = service.validate_audio(audio, "runway")

    # 2. 結果を DB に保存する
    result = service.validate_image(image, "runway", save=True)

    # 3. 結果の利用
    if result.is_valid:
        # 生成処理へ進む
        pass
    elif result.is_unsupported:
        print(f"{result.provider_key} は {result.asset_type} の直接入力に未対応")
    else:
        for err in result.errors:
            print(f"[ERROR][{err.field}] {err.message}")
        for warn in result.warnings:
            print(f"[WARN][{err.field}] {warn.message}")

注意:
  - バリデーション本体（共通 + プロバイダー固有）はプロバイダークラスが担う
  - このサービスはモデル変換・呼び出し・保存の連携を担うだけで、判定ロジックを持たない
  - 既存の views.py は registry.validate_content() を直接呼んでいるため、このサービスは不要
  - 新たに「DB から取得して判定 + 結果を保存したい」ユースケース向けのエントリーポイント
"""
from __future__ import annotations

from aivideo_component.models import GeneratedAudio, GeneratedImage
from aivideo_component.validation.protocol import (
    AudioMeta,
    ContentValidationInput,
    ContentValidationResult,
    ImageMeta,
)
from aivideo_component.validation.registry import get_validator


class ContentValidationService:
    """
    DB保存済みメタ情報を使って provider 別バリデーションを実行するサービス。
    """

    # ────────────────────────────────────────────────────────────────
    # 公開メソッド
    # ────────────────────────────────────────────────────────────────

    def validate_image(
        self,
        image: GeneratedImage,
        provider_key: str,
        *,
        save: bool = False,
    ) -> ContentValidationResult:
        """
        GeneratedImage の保存済みメタ情報を使って provider 別バリデーションを実行する。

        共通バリデーションはプロバイダークラス内部で実行されるため、
        このメソッドはモデル変換・呼び出し・保存の連携のみを行う。

        Args:
            image: バリデーション対象の GeneratedImage インスタンス
            provider_key: "runway" | "pika" | "kling" など
            save: True の場合、結果を image の validation_status / validation_message に保存する
        Returns:
            ContentValidationResult
        """
        validation_input = ContentValidationInput(
            provider_key=provider_key,
            image=self._image_to_meta(image),
        )
        result = get_validator(provider_key).validate(validation_input)
        result.provider_key = provider_key
        result.asset_type = "image"

        if save:
            self._save_image_result(image, result)

        return result

    def validate_audio(
        self,
        audio: GeneratedAudio,
        provider_key: str,
        *,
        save: bool = False,
    ) -> ContentValidationResult:
        """
        GeneratedAudio の保存済みメタ情報を使って provider 別バリデーションを実行する。

        Args:
            audio: バリデーション対象の GeneratedAudio インスタンス
            provider_key: "runway" | "pika" | "kling" など
            save: True の場合、結果を audio の validation_status / validation_message に保存する
        Returns:
            ContentValidationResult
        """
        validation_input = ContentValidationInput(
            provider_key=provider_key,
            audio=self._audio_to_meta(audio),
        )
        result = get_validator(provider_key).validate(validation_input)
        result.provider_key = provider_key
        result.asset_type = "audio"

        if save:
            self._save_audio_result(audio, result)

        return result

    # ────────────────────────────────────────────────────────────────
    # モデル → メタデータ変換（実ファイルを読み込まない）
    # ────────────────────────────────────────────────────────────────

    @staticmethod
    def _image_to_meta(image: GeneratedImage) -> ImageMeta:
        return ImageMeta(
            image_id=image.pk,
            mime_type=image.mime_type,
            file_size_bytes=image.file_size_bytes,
            width=image.width,
            height=image.height,
            aspect_ratio=image.aspect_ratio,
        )

    @staticmethod
    def _audio_to_meta(audio: GeneratedAudio) -> AudioMeta:
        return AudioMeta(
            audio_id=audio.pk,
            mime_type=audio.mime_type,
            file_size_bytes=audio.file_size_bytes,
            duration_sec=audio.duration_sec,
            sample_rate=audio.sample_rate,
            channels=audio.channels,
            codec=audio.codec,
        )

    # ────────────────────────────────────────────────────────────────
    # 結果 → 既存カラムへの保存
    # ────────────────────────────────────────────────────────────────

    @staticmethod
    def _result_to_status(result: ContentValidationResult) -> str:
        """ContentValidationResult を validation_status の選択肢文字列に変換する。"""
        if not result.is_valid:
            return GeneratedImage.VALIDATION_INVALID   # "invalid"
        if result.warnings:
            return GeneratedImage.VALIDATION_WARNING   # "warning"
        return GeneratedImage.VALIDATION_VALID         # "valid"

    @staticmethod
    def _result_to_message(result: ContentValidationResult) -> str:
        """ContentValidationResult を人間が読める validation_message 文字列に変換する。"""
        provider = result.provider_key or "unknown"
        lines: list[str] = []

        if result.is_unsupported:
            lines.append(
                f"[{provider}] 未対応: このプロバイダーは "
                f"{result.asset_type or 'このアセット種別'} の直接入力に対応していません"
            )
            # unsupported でも errors にメッセージが入っている場合は表示する
            for err in result.errors:
                lines.append(f"  詳細: {err.message}")
            return "\n".join(lines)

        for err in result.errors:
            lines.append(f"[{provider}][ERROR][{err.field}] {err.message}")

        for warn in result.warnings:
            lines.append(f"[{provider}][WARN][{warn.field}] {warn.message}")

        if not lines:
            asset = result.asset_type or "コンテンツ"
            lines.append(f"[{provider}] {asset} は送信可能です")

        return "\n".join(lines)

    def _save_image_result(
        self, image: GeneratedImage, result: ContentValidationResult
    ) -> None:
        """バリデーション結果を GeneratedImage の既存カラムに保存する（スキーマ変更なし）。"""
        image.validation_status = self._result_to_status(result)
        image.validation_message = self._result_to_message(result)
        # auto_now=True の updated_at も含めて明示的に指定する
        image.save(update_fields=["validation_status", "validation_message", "updated_at"])

    def _save_audio_result(
        self, audio: GeneratedAudio, result: ContentValidationResult
    ) -> None:
        """バリデーション結果を GeneratedAudio の既存カラムに保存する（スキーマ変更なし）。"""
        audio.validation_status = self._result_to_status(result)
        audio.validation_message = self._result_to_message(result)
        audio.save(update_fields=["validation_status", "validation_message", "updated_at"])
