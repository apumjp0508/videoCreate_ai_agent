"""
メタ情報をモデルインスタンスに保存するサービス。

責務:
  - extractor を呼んで RawMetadata を取得する
  - モデルに存在するフィールドだけを動的にセットして save() する
  - 失敗してもアップロード本体を壊さない（ログのみ）

将来の拡張ポイント:
  - apply_*_metadata の後に provider 適合判定を呼ぶ処理を追加できる
  - 例: validate_for_provider(instance, provider_key) を同一モジュールに追加
"""
from __future__ import annotations

import logging

from .audio import RawAudioMetadata, extract_audio_metadata
from .image import RawImageMetadata, extract_image_metadata

logger = logging.getLogger(__name__)


def apply_image_metadata(instance, file) -> None:
    """
    画像ファイルのメタ情報を抽出して instance の各フィールドに保存する。

    Args:
        instance: GeneratedImage のインスタンス（保存済み、pk あり）
        file:     Django UploadedFile（アップロードされた画像ファイル）
    """
    try:
        meta = extract_image_metadata(file)
        update_fields: list[str] = []
        _assign(instance, 'original_filename', meta.original_filename, update_fields)
        _assign(instance, 'mime_type',         meta.mime_type,         update_fields)
        _assign(instance, 'file_size_bytes',   meta.file_size_bytes,   update_fields)
        _assign(instance, 'width',             meta.width,             update_fields)
        _assign(instance, 'height',            meta.height,            update_fields)
        _assign(instance, 'aspect_ratio',      meta.aspect_ratio,      update_fields)
        if update_fields:
            instance.save(update_fields=update_fields)
            logger.info(
                'Image metadata saved (pk=%s, fields=%s)',
                getattr(instance, 'pk', '?'),
                update_fields,
            )
    except Exception as exc:
        logger.error(
            'apply_image_metadata failed (pk=%s): %s',
            getattr(instance, 'pk', '?'),
            exc,
        )


def apply_audio_metadata(instance, file) -> None:
    """
    音声ファイルのメタ情報を抽出して instance の各フィールドに保存する。

    Args:
        instance: GeneratedAudio のインスタンス（保存済み、pk あり）
        file:     Django UploadedFile（アップロードされた音声ファイル）
    """
    try:
        meta = extract_audio_metadata(file)
        update_fields: list[str] = []
        _assign(instance, 'original_filename', meta.original_filename, update_fields)
        _assign(instance, 'mime_type',         meta.mime_type,         update_fields)
        _assign(instance, 'file_size_bytes',   meta.file_size_bytes,   update_fields)
        _assign(instance, 'duration_sec',      meta.duration_sec,      update_fields)
        _assign(instance, 'sample_rate',       meta.sample_rate,       update_fields)
        _assign(instance, 'channels',          meta.channels,          update_fields)
        _assign(instance, 'codec',             meta.codec,             update_fields)
        if update_fields:
            instance.save(update_fields=update_fields)
            logger.info(
                'Audio metadata saved (pk=%s, fields=%s)',
                getattr(instance, 'pk', '?'),
                update_fields,
            )
    except Exception as exc:
        logger.error(
            'apply_audio_metadata failed (pk=%s): %s',
            getattr(instance, 'pk', '?'),
            exc,
        )


def _assign(instance, field_name: str, value, update_fields: list[str]) -> None:
    """モデルにフィールドが存在する場合のみ値をセットしてフィールド名を記録する。"""
    if hasattr(instance, field_name):
        setattr(instance, field_name, value)
        update_fields.append(field_name)
