"""
画像ファイルからメタ情報を抽出する。

- モデルを知らない（疎結合）
- ファイルポインタは呼び出し前後で seek(0) を保証する
- 各処理は独立して try/except するため、部分的な失敗でも取得できた値を返す
- 将来 ffprobe など別ライブラリへの差し替えはここだけ変える
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from math import gcd

logger = logging.getLogger(__name__)


@dataclass
class RawImageMetadata:
    """Pillow / python-magic で抽出した生のメタ情報。DB やモデルを意識しない。"""
    original_filename: str
    mime_type: str
    file_size_bytes: int | None
    width: int | None
    height: int | None
    aspect_ratio: str  # 例: "16:9", "1:1", "9:16"


def extract_image_metadata(file) -> RawImageMetadata:
    """
    Django UploadedFile から画像メタ情報を抽出して RawImageMetadata を返す。

    将来 provider 適合判定を実装する際は、この戻り値を直接渡せる。
    """
    original_filename = getattr(file, 'name', '') or ''
    file_size_bytes: int | None = getattr(file, 'size', None)
    mime_type = ''
    width: int | None = None
    height: int | None = None
    aspect_ratio = ''

    # ファイル内容を一括読み込み（以降の処理でポインタ位置に依存しない）
    data: bytes | None = None
    try:
        file.seek(0)
        data = file.read()
        file.seek(0)
    except Exception as exc:
        logger.warning('Failed to read image file "%s": %s', original_filename, exc)
        return RawImageMetadata(
            original_filename=original_filename,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
        )

    # MIME タイプ判定（python-magic）
    try:
        import magic
        mime_type = magic.from_buffer(data[:2048], mime=True)
    except Exception as exc:
        logger.warning('MIME type detection failed for "%s": %s', original_filename, exc)

    # 画像サイズ取得（Pillow）
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        width, height = img.size
    except Exception as exc:
        logger.warning('Pillow failed to read dimensions for "%s": %s', original_filename, exc)

    # アスペクト比計算
    if width and height:
        g = gcd(width, height)
        aspect_ratio = f'{width // g}:{height // g}'

    return RawImageMetadata(
        original_filename=original_filename,
        mime_type=mime_type,
        file_size_bytes=file_size_bytes,
        width=width,
        height=height,
        aspect_ratio=aspect_ratio,
    )
