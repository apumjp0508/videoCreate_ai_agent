"""
バリデーションサービス層。2つのクラスで構成される。

─────────────────────────────────────────────────────────────
ContentValidationService
  DB保存済みメタ情報を使ったバリデーション実行・保存のエントリーポイント。
  内部で ProviderConfigRepository + DbDrivenContentValidator を直接使う。
  registry.py は import しない（循環インポート回避）。

  使い方::
    service = ContentValidationService()
    result = service.validate_image(image, "runway")          # 結果取得のみ
    result = service.validate_image(image, "runway", save=True) # DB 保存あり

─────────────────────────────────────────────────────────────
ProviderConfigRepository / DbDrivenContentValidator
  registry.py から呼ばれる DB 駆動バリデーターの実体。
  provider_id または provider_key から VideoAiProviderValidationConfig を取得し、
  その値に基づいてバリデーションを実行する。

  直接使う場合::
    # provider_key で取得
    config = ProviderConfigRepository().get_by_provider_key('runway')

    # provider_id (PK) で取得
    config = ProviderConfigRepository().get_by_provider_id(3)

    # 全アクティブプロバイダーを一括チェック（どのAIで使えるか確認）
    for config in ProviderConfigRepository().get_all_active():
        result = DbDrivenContentValidator(config).validate(input)
"""
from __future__ import annotations

from dataclasses import dataclass, field

from aivideo_component.models import GeneratedAudio, GeneratedImage
from aivideo_component.validation.common import (
    validate_audio_common,
    validate_image_common,
)
from aivideo_component.validation.protocol import (
    AudioMeta,
    ContentValidationInput,
    ContentValidationResult,
    ImageMeta,
)


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
        config = ProviderConfigRepository().get_by_provider_key(provider_key)
        result = DbDrivenContentValidator(config).validate(validation_input)
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
        config = ProviderConfigRepository().get_by_provider_key(provider_key)
        result = DbDrivenContentValidator(config).validate(validation_input)
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


# ─────────────────────────────────────────────────────────────
# in-memory 設定値（Django ORM に依存しない）
# ─────────────────────────────────────────────────────────────

@dataclass
class ProviderValidationConfig:
    """
    DB の VideoAiProviderValidationConfig を in-memory に変換した設定値。
    バリデーター側が Django ORM を直接知らなくて済むように隔離する。
    """
    provider_id: int
    provider_key: str
    provider_name: str

    # 画像
    image_allowed_mime_types: list[str] = field(default_factory=list)
    image_max_size_bytes: int | None = None
    image_max_size_soft_bytes: int | None = None
    image_min_dimension: int | None = None
    image_max_dimension: int | None = None
    image_min_dimension_recommended: int | None = None
    image_max_dimension_recommended: int | None = None
    image_allowed_aspect_ratios: list[str] | None = None  # None = 制限なし
    image_aspect_ratio_required: bool = False

    # 音声
    audio_is_supported: bool = True
    audio_unsupported_message: str | None = None
    audio_allowed_mime_types: list[str] | None = None     # None = 共通チェックのみ
    audio_max_size_bytes: int | None = None
    audio_max_duration_sec: float | None = None
    audio_min_sample_rate: int | None = None
    audio_max_sample_rate: int | None = None
    audio_allowed_channels: list[int] | None = None       # None = 共通チェックのみ


# ─────────────────────────────────────────────────────────────
# DB 取得層（ここだけ Django ORM に触れる）
# ─────────────────────────────────────────────────────────────

class ProviderConfigNotFoundError(Exception):
    pass


class ProviderConfigRepository:
    """
    VideoAiProviderValidationConfig を DB から取得して
    ProviderValidationConfig dataclass に変換する。
    """

    def get_by_provider_key(self, provider_key: str) -> ProviderValidationConfig:
        """
        provider_key ("runway" など) に対応する設定を返す。

        Raises:
            ProviderConfigNotFoundError: DB にレコードがない場合
        """
        from video_ai.models import VideoAiProvider
        try:
            provider = (
                VideoAiProvider.objects
                .select_related('validation_config')
                .get(provider_key=provider_key, is_active=True)
            )
        except VideoAiProvider.DoesNotExist:
            raise ProviderConfigNotFoundError(
                f"provider_key={provider_key!r} のプロバイダーが見つかりません"
            )
        return self._to_config(provider)

    def get_by_provider_id(self, provider_id: int) -> ProviderValidationConfig:
        """
        provider_id (PK) に対応する設定を返す。
        View や Job から provider_id だけ渡してバリデーションしたい場合に使う。

        Raises:
            ProviderConfigNotFoundError: DB にレコードがない場合
        """
        from video_ai.models import VideoAiProvider
        try:
            provider = (
                VideoAiProvider.objects
                .select_related('validation_config')
                .get(pk=provider_id, is_active=True)
            )
        except VideoAiProvider.DoesNotExist:
            raise ProviderConfigNotFoundError(
                f"provider_id={provider_id} のプロバイダーが見つかりません"
            )
        return self._to_config(provider)

    def get_all_active(self) -> list[ProviderValidationConfig]:
        """
        is_active=True かつ validation_config を持つ全プロバイダーの設定を返す。
        「この画像はどのAIで使えるか」一括チェックに使う。
        """
        from video_ai.models import VideoAiProvider
        providers = (
            VideoAiProvider.objects
            .select_related('validation_config')
            .filter(is_active=True)
        )
        return [
            self._to_config(p)
            for p in providers
            if hasattr(p, 'validation_config')
        ]

    def _to_config(self, provider) -> ProviderValidationConfig:
        if not hasattr(provider, 'validation_config'):
            raise ProviderConfigNotFoundError(
                f"provider_key={provider.provider_key!r} に validation_config がありません"
            )
        cfg = provider.validation_config
        return ProviderValidationConfig(
            provider_id=provider.pk,
            provider_key=provider.provider_key,
            provider_name=provider.provider_name,
            image_allowed_mime_types=cfg.image_allowed_mime_types or [],
            image_max_size_bytes=cfg.image_max_size_bytes,
            image_max_size_soft_bytes=cfg.image_max_size_soft_bytes,
            image_min_dimension=cfg.image_min_dimension,
            image_max_dimension=cfg.image_max_dimension,
            image_min_dimension_recommended=cfg.image_min_dimension_recommended,
            image_max_dimension_recommended=cfg.image_max_dimension_recommended,
            image_allowed_aspect_ratios=cfg.image_allowed_aspect_ratios,
            image_aspect_ratio_required=cfg.image_aspect_ratio_required,
            audio_is_supported=cfg.audio_is_supported,
            audio_unsupported_message=cfg.audio_unsupported_message,
            audio_allowed_mime_types=cfg.audio_allowed_mime_types,
            audio_max_size_bytes=cfg.audio_max_size_bytes,
            audio_max_duration_sec=cfg.audio_max_duration_sec,
            audio_min_sample_rate=cfg.audio_min_sample_rate,
            audio_max_sample_rate=cfg.audio_max_sample_rate,
            audio_allowed_channels=cfg.audio_allowed_channels,
        )


# ─────────────────────────────────────────────────────────────
# DB 駆動バリデーター（Django ORM を知らない）
# ─────────────────────────────────────────────────────────────

class DbDrivenContentValidator:
    """
    ProviderValidationConfig（DB 由来の設定値）を使ってバリデーションを行う。
    既存の ContentValidatorProtocol と同じ validate() シグネチャを持つ。
    """

    def __init__(self, config: ProviderValidationConfig) -> None:
        self._cfg = config

    def validate(self, input: ContentValidationInput) -> ContentValidationResult:
        result = ContentValidationResult(is_valid=True)
        result.provider_key = self._cfg.provider_key

        if input.image is not None:
            result.asset_type = 'image'
            validate_image_common(input.image, result)   # 共通チェック（コード側）
            self._validate_image(input, result)          # プロバイダー固有（DB値）

        if input.audio is not None:
            result.asset_type = 'audio'
            if not self._cfg.audio_is_supported:
                result.is_unsupported = True
                result.add_error(
                    'audio',
                    self._cfg.audio_unsupported_message
                    or f"{self._cfg.provider_name}: 音声入力は未対応です",
                )
                return result
            validate_audio_common(input.audio, result)   # 共通チェック
            self._validate_audio(input, result)          # プロバイダー固有

        return result

    # ── 画像 ─────────────────────────────────────────────────────

    def _validate_image(
        self, input: ContentValidationInput, result: ContentValidationResult
    ) -> None:
        img = input.image
        cfg = self._cfg
        name = cfg.provider_name

        # MIME タイプ
        # 共通チェックを通過したが当プロバイダーで非対応のものだけ追加エラーを出す
        if img.mime_type and cfg.image_allowed_mime_types:
            from aivideo_component.validation import constants as C
            if (img.mime_type in C.COMMON_IMAGE_ALLOWED_MIME
                    and img.mime_type not in cfg.image_allowed_mime_types):
                result.add_error(
                    'image',
                    f"{name}: 非対応の画像形式です: {img.mime_type!r}  "
                    f"（対応: {', '.join(sorted(cfg.image_allowed_mime_types))}）",
                )

        # ファイルサイズ (hard → error)
        if img.file_size_bytes is not None and cfg.image_max_size_bytes is not None:
            if img.file_size_bytes > cfg.image_max_size_bytes:
                result.add_error(
                    'image',
                    f"{name}: ファイルサイズが上限を超えています: "
                    f"{img.file_size_bytes / 1024 / 1024:.1f}MB  "
                    f"（上限: {cfg.image_max_size_bytes // (1024 * 1024)}MB）",
                )
            # ファイルサイズ (soft → warning)
            elif (cfg.image_max_size_soft_bytes is not None
                    and img.file_size_bytes > cfg.image_max_size_soft_bytes):
                result.add_warning(
                    'image',
                    f"{name}: ファイルサイズが推奨上限を超えています: "
                    f"{img.file_size_bytes / 1024 / 1024:.1f}MB  "
                    f"（推奨上限: {cfg.image_max_size_soft_bytes // (1024 * 1024)}MB）",
                )

        # 解像度 (hard → error)
        for dim_name, dim_val in [('幅', img.width), ('高さ', img.height)]:
            if dim_val is None:
                continue
            if cfg.image_min_dimension is not None and dim_val < cfg.image_min_dimension:
                result.add_error(
                    'image',
                    f"{name}: 画像の{dim_name}が最小値を下回っています: {dim_val}px  "
                    f"（最小: {cfg.image_min_dimension}px）",
                )
            if cfg.image_max_dimension is not None and dim_val > cfg.image_max_dimension:
                result.add_error(
                    'image',
                    f"{name}: 画像の{dim_name}が最大値を超えています: {dim_val}px  "
                    f"（最大: {cfg.image_max_dimension}px）",
                )

        # 解像度 (soft → warning)
        for dim_name, dim_val in [('幅', img.width), ('高さ', img.height)]:
            if dim_val is None:
                continue
            if (cfg.image_min_dimension_recommended is not None
                    and dim_val < cfg.image_min_dimension_recommended):
                result.add_warning(
                    'image',
                    f"{name}: 画像の{dim_name}が推奨値を下回っています: {dim_val}px  "
                    f"（推奨: {cfg.image_min_dimension_recommended}px 以上）",
                )
            elif (cfg.image_max_dimension_recommended is not None
                    and dim_val > cfg.image_max_dimension_recommended):
                result.add_warning(
                    'image',
                    f"{name}: 画像の{dim_name}が推奨上限を超えています: {dim_val}px  "
                    f"（推奨上限: {cfg.image_max_dimension_recommended}px）",
                )

        # アスペクト比（image_allowed_aspect_ratios が null でない場合のみチェック）
        if cfg.image_allowed_aspect_ratios is not None:
            self._validate_aspect_ratio(img.aspect_ratio, result)

    def _validate_aspect_ratio(
        self, aspect_ratio: str, result: ContentValidationResult
    ) -> None:
        cfg = self._cfg
        name = cfg.provider_name
        allowed = cfg.image_allowed_aspect_ratios

        if not aspect_ratio:
            result.add_warning(
                'image',
                f"{name}: アスペクト比が未設定です。"
                f"生成時に想定外のトリミングが発生する可能性があります。",
            )
            return

        if aspect_ratio not in allowed:
            msg = (
                f"{name}: アスペクト比が対応値外です: {aspect_ratio!r}  "
                f"（対応: {', '.join(sorted(allowed))}）"
            )
            if cfg.image_aspect_ratio_required:
                result.add_error('image', msg)
            else:
                result.add_warning('image', msg)

    # ── 音声 ─────────────────────────────────────────────────────

    def _validate_audio(
        self, input: ContentValidationInput, result: ContentValidationResult
    ) -> None:
        audio = input.audio
        cfg = self._cfg
        name = cfg.provider_name

        # MIME タイプ（プロバイダー固有リストがある場合のみ）
        if audio.mime_type and cfg.audio_allowed_mime_types is not None:
            from aivideo_component.validation import constants as C
            if (audio.mime_type in C.COMMON_AUDIO_ALLOWED_MIME
                    and audio.mime_type not in cfg.audio_allowed_mime_types):
                result.add_error(
                    'audio',
                    f"{name}: 非対応の音声形式です: {audio.mime_type!r}  "
                    f"（対応: {', '.join(sorted(cfg.audio_allowed_mime_types))}）",
                )

        # ファイルサイズ
        if (audio.file_size_bytes is not None
                and cfg.audio_max_size_bytes is not None
                and audio.file_size_bytes > cfg.audio_max_size_bytes):
            result.add_error(
                'audio',
                f"{name}: 音声ファイルサイズが上限を超えています: "
                f"{audio.file_size_bytes / 1024 / 1024:.1f}MB  "
                f"（上限: {cfg.audio_max_size_bytes // (1024 * 1024)}MB）",
            )

        # 長さ（プロバイダー固有の上限がある場合のみ。共通は common.py で処理済み）
        if (audio.duration_sec is not None
                and cfg.audio_max_duration_sec is not None
                and audio.duration_sec > cfg.audio_max_duration_sec):
            result.add_error(
                'audio',
                f"{name}: 音声が長すぎます: {audio.duration_sec:.1f}秒  "
                f"（上限: {cfg.audio_max_duration_sec:.0f}秒）",
            )

        # サンプルレート（プロバイダー固有の範囲がある場合のみ）
        if audio.sample_rate is not None:
            min_sr = cfg.audio_min_sample_rate
            max_sr = cfg.audio_max_sample_rate
            if min_sr is not None and max_sr is not None:
                if not (min_sr <= audio.sample_rate <= max_sr):
                    result.add_error(
                        'audio',
                        f"{name}: サンプルレートが範囲外です: {audio.sample_rate} Hz  "
                        f"（{min_sr}〜{max_sr} Hz）",
                    )

        # チャンネル数（プロバイダー固有リストがある場合のみ）
        if (audio.channels is not None
                and cfg.audio_allowed_channels is not None
                and audio.channels not in cfg.audio_allowed_channels):
            result.add_error(
                'audio',
                f"{name}: 非対応のチャンネル数です: {audio.channels}ch  "
                f"（対応: {sorted(cfg.audio_allowed_channels)}）",
            )
