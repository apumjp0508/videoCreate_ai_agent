"""
音声ファイルからメタ情報を抽出する。

- モデルを知らない（疎結合）
- ファイルポインタは呼び出し前後で seek(0) を保証する
- 各処理は独立して try/except するため、部分的な失敗でも取得できた値を返す
- 将来 ffprobe など別ライブラリへの差し替えはここだけ変える
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# mutagen のクラス名 → 短いコーデック文字列
_MUTAGEN_CODEC_MAP: dict[str, str] = {
    'MP3': 'mp3',
    'FLAC': 'flac',
    'OggVorbis': 'ogg',
    'OggOpus': 'opus',
    'OggFLAC': 'ogg',
    'OggSpeex': 'ogg',
    'WAVE': 'wav',
    'AIFF': 'aiff',
    'MP4': 'aac',       # .m4a / .aac
    'ASF': 'wma',
    'MonkeysAudio': 'ape',
    'WavPack': 'wv',
    'TrueAudio': 'tta',
    'Musepack': 'mpc',
    'OptimFROG': 'ofr',
    'DSDIFF': 'dsd',
    'DSF': 'dsf',
    'AAC': 'aac',
    'AC3': 'ac3',
    'SMF': 'midi',
}


@dataclass
class RawAudioMetadata:
    """mutagen / python-magic で抽出した生のメタ情報。DB やモデルを意識しない。"""
    original_filename: str
    mime_type: str
    file_size_bytes: int | None
    duration_sec: float | None   # 秒単位
    sample_rate: int | None      # Hz 単位
    channels: int | None         # 1=モノラル, 2=ステレオ
    codec: str                   # 例: "mp3", "aac", "wav"


def extract_audio_metadata(file) -> RawAudioMetadata:
    """
    Django UploadedFile から音声メタ情報を抽出して RawAudioMetadata を返す。

    将来 provider 適合判定を実装する際は、この戻り値を直接渡せる。
    """
    original_filename = getattr(file, 'name', '') or ''
    file_size_bytes: int | None = getattr(file, 'size', None)
    mime_type = ''
    duration_sec: float | None = None
    sample_rate: int | None = None
    channels: int | None = None
    codec = ''

    # ファイル内容を一括読み込み（以降の処理でポインタ位置に依存しない）
    data: bytes | None = None
    try:
        file.seek(0)
        data = file.read()
        file.seek(0)
    except Exception as exc:
        logger.warning('Failed to read audio file "%s": %s', original_filename, exc)
        return RawAudioMetadata(
            original_filename=original_filename,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            duration_sec=duration_sec,
            sample_rate=sample_rate,
            channels=channels,
            codec=codec,
        )

    # MIME タイプ判定（python-magic）
    try:
        import magic
        mime_type = magic.from_buffer(data[:2048], mime=True)
    except Exception as exc:
        logger.warning('MIME type detection failed for "%s": %s', original_filename, exc)

    # 音声情報取得（mutagen）
    # BytesIO に .name を付与することで、拡張子ヒントを mutagen に渡す
    try:
        import mutagen
        buf = io.BytesIO(data)
        buf.name = original_filename
        audio = mutagen.File(buf)
        if audio is not None and audio.info is not None:
            duration_sec = getattr(audio.info, 'length', None)
            sample_rate = getattr(audio.info, 'sample_rate', None)
            channels = getattr(audio.info, 'channels', None)
            class_name = type(audio).__name__
            codec = _MUTAGEN_CODEC_MAP.get(class_name, class_name.lower())
    except Exception as exc:
        logger.warning('mutagen failed to read audio info for "%s": %s', original_filename, exc)

    return RawAudioMetadata(
        original_filename=original_filename,
        mime_type=mime_type,
        file_size_bytes=file_size_bytes,
        duration_sec=duration_sec,
        sample_rate=sample_rate,
        channels=channels,
        codec=codec,
    )
