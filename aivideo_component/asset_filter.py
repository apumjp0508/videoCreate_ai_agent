"""
選択された AI プロバイダーで使える素材をフィルタリングする。

返す構造を valid / invalid + reasons に分けることで、
View は「表示するか」を、テンプレートは「なぜ使えないか」をそれぞれ判断できる。

Usage::

    from aivideo_component.asset_filter import filter_assets_for_provider

    result = filter_assets_for_provider("runway", images_qs, audios_qs)

    # 全件（テンプレートで valid/invalid を自分で振り分けたい場合）
    for fi in result.images:
        fi.image          # GeneratedImage
        fi.is_valid       # bool
        fi.errors         # list[str]  ← 空 → 使用可能
        fi.warnings       # list[str]  ← 空 → 警告なし

    # プロパティで絞り込み済みリストを取得
    result.valid_images    # list[FilteredImage]  errors が空のもの
    result.invalid_images  # list[FilteredImage]  errors が1件以上のもの
    result.valid_audios
    result.invalid_audios
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from aivideo_component.models import GeneratedAudio, GeneratedImage
from aivideo_component.validation.service import (
    ContentValidationService,
    ProviderConfigNotFoundError,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# 1件あたりの結果
# ─────────────────────────────────────────────────────────────

@dataclass
class FilteredImage:
    """画像1件のフィルタリング結果。"""
    image: GeneratedImage
    errors: list[str] = field(default_factory=list)    # 空 → 使用可能
    warnings: list[str] = field(default_factory=list)  # 空 → 警告なし

    @property
    def is_valid(self) -> bool:
        """errors が空なら使用可能。"""
        return not self.errors


@dataclass
class FilteredAudio:
    """音声1件のフィルタリング結果。"""
    audio: GeneratedAudio
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


# ─────────────────────────────────────────────────────────────
# 一括フィルタリング結果
# ─────────────────────────────────────────────────────────────

@dataclass
class AssetFilterResult:
    """
    filter_assets_for_provider() の戻り値。

    images / audios には全件が入る。
    is_valid で絞り込んだプロパティも提供するので、
    テンプレートや View で用途に応じて使い分ける。
    """
    images: list[FilteredImage] = field(default_factory=list)
    audios: list[FilteredAudio] = field(default_factory=list)
    provider_key: str = ""

    @property
    def valid_images(self) -> list[FilteredImage]:
        return [fi for fi in self.images if fi.is_valid]

    @property
    def invalid_images(self) -> list[FilteredImage]:
        return [fi for fi in self.images if not fi.is_valid]

    @property
    def valid_audios(self) -> list[FilteredAudio]:
        return [fa for fa in self.audios if fa.is_valid]

    @property
    def invalid_audios(self) -> list[FilteredAudio]:
        return [fa for fa in self.audios if not fa.is_valid]


# ─────────────────────────────────────────────────────────────
# フィルタリング関数
# ─────────────────────────────────────────────────────────────

def filter_assets_for_provider(
    provider_key: str,
    images: list[GeneratedImage],
    audios: list[GeneratedAudio],
) -> AssetFilterResult:
    """
    指定プロバイダーで使える素材をフィルタリングする。

    各素材に対してバリデーションを実行し、valid / invalid + 理由を返す。
    DB 保存は行わない（validate_image / validate_audio の save=False）。

    Args:
        provider_key: "runway" | "pika" | "kling" など
        images: フィルタリング対象の GeneratedImage リスト
        audios: フィルタリング対象の GeneratedAudio リスト

    Returns:
        AssetFilterResult

    Raises:
        ProviderConfigNotFoundError: provider_key に対応する ValidationConfig が DB にない場合
    """
    service = ContentValidationService()
    result = AssetFilterResult(provider_key=provider_key)

    for image in images:
        try:
            validation = service.validate_image(image, provider_key)
            result.images.append(FilteredImage(
                image=image,
                errors=[issue.message for issue in validation.errors],
                warnings=[issue.message for issue in validation.warnings],
            ))
        except ProviderConfigNotFoundError:
            raise
        except Exception as exc:
            # 個別素材の予期しないエラーはスキップして続行
            logger.warning(
                "filter_assets_for_provider: image pk=%s のバリデーション中にエラー: %s",
                image.pk, exc,
            )
            result.images.append(FilteredImage(image=image))

    for audio in audios:
        try:
            validation = service.validate_audio(audio, provider_key)
            result.audios.append(FilteredAudio(
                audio=audio,
                errors=[issue.message for issue in validation.errors],
                warnings=[issue.message for issue in validation.warnings],
            ))
        except ProviderConfigNotFoundError:
            raise
        except Exception as exc:
            logger.warning(
                "filter_assets_for_provider: audio pk=%s のバリデーション中にエラー: %s",
                audio.pk, exc,
            )
            result.audios.append(FilteredAudio(audio=audio))

    return result
