"""
ffmpeg を使って動画ファイルから音声を抽出するユーティリティ。

Temporal / Django / OpenAI に依存しない独立モジュール。
単体テストや別サービスからも直接利用できる。

使い方:
    from temporal.activities.video_metadata.pipeline.audio_extractor import extract_audio_from_video

    audio_path = await extract_audio_from_video("/tmp/video.mp4")
    try:
        # audio_path を使って処理
        ...
    finally:
        audio_path.unlink(missing_ok=True)
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioExtractionError(Exception):
    """ffmpeg による音声抽出に失敗した場合。"""


async def extract_audio_from_video(
    video_path: str | Path,
    *,
    output_format: str = "mp3",
    sample_rate: int = 16_000,
    channels: int = 1,
) -> Path:
    """
    動画ファイルから音声を抽出して一時ファイルとして返す。

    Whisper API の推奨設定（16 kHz / モノラル）に合わせたデフォルト値を使用する。
    返り値のパスは呼び出し元で必ず削除すること（try/finally 推奨）。

    Args:
        video_path:    入力動画ファイルのパス
        output_format: 出力音声フォーマット（mp3 / wav / m4a など）
        sample_rate:   サンプルレート Hz（Whisper 推奨: 16000）
        channels:      チャンネル数（1=モノラル / 2=ステレオ）

    Returns:
        抽出された音声の一時ファイルパス

    Raises:
        AudioExtractionError: ffmpeg の実行に失敗した場合
        FileNotFoundError:    ffmpeg がインストールされていない場合
    """
    video_path = Path(video_path)
    suffix = f".{output_format}"

    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.close()
    output_path = Path(tmp.name)

    cmd = [
        "ffmpeg",
        "-y",                         # 上書き確認なし
        "-i", str(video_path),        # 入力
        "-vn",                        # 映像ストリーム除去
        "-ar", str(sample_rate),      # サンプルレート
        "-ac", str(channels),         # チャンネル数
        "-f", output_format,          # 出力フォーマット
        str(output_path),
    ]

    logger.debug("Running ffmpeg: %s", " ".join(cmd))

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        output_path.unlink(missing_ok=True)
        raise AudioExtractionError(
            f"ffmpeg failed (returncode={proc.returncode}): {stderr.decode(errors='replace')}"
        )

    size_bytes = output_path.stat().st_size
    logger.info(
        "Audio extracted: %s  format=%s  sample_rate=%d  size=%d bytes",
        output_path.name, output_format, sample_rate, size_bytes,
    )
    return output_path
