"""
ffmpeg を使って動画ファイルから一定間隔でスナップショット（静止画）を抽出するユーティリティ。

Temporal / Django / OpenAI に依存しない独立モジュール。
単体テストや別サービスからも直接利用できる。

使い方:
    from temporal.activities.thumbnail_generation.pipeline.snapshot_extractor import (
        extract_snapshots,
    )

    snapshots = await extract_snapshots("/tmp/video.mp4")
    try:
        # snapshots を使って処理
        ...
    finally:
        for p in snapshots:
            p.unlink(missing_ok=True)
        snapshots[0].parent.rmdir()   # 空になった一時ディレクトリを削除
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class SnapshotExtractionError(Exception):
    """ffmpeg によるスナップショット抽出に失敗した場合。"""


async def extract_snapshots(
    video_path: str | Path,
    *,
    interval_sec: float = 1.0,
    output_format: str = "jpg",
    quality: int = 2,
    max_snapshots: int | None = None,
) -> list[Path]:
    """
    動画ファイルから一定間隔でスナップショットを抽出して返す。

    返り値のパスリストは呼び出し元で必ず削除すること（try/finally 推奨）。
    すべてのファイルは同一の一時ディレクトリに格納される。

    Args:
        video_path:     入力動画ファイルのパス
        interval_sec:   スナップショットの間隔（秒）
        output_format:  出力画像フォーマット（"jpg" / "png"）
        quality:        ffmpeg の -q:v 値（1=最高品質 / 31=最低品質、jpg の場合）
        max_snapshots:  取得する最大スナップショット数（None で無制限）
                        指定した場合、超過分は切り捨てられる。

    Returns:
        抽出されたスナップショットの Path リスト（時系列昇順）

    Raises:
        SnapshotExtractionError: ffmpeg 実行に失敗した場合
        FileNotFoundError:       ffmpeg がインストールされていない場合
    """
    video_path = Path(video_path)
    output_dir = Path(tempfile.mkdtemp(prefix="thumbnails_"))
    pattern = str(output_dir / f"snapshot_%06d.{output_format}")

    # fps フィルタ: 1/interval_sec フレーム/秒 を抽出
    fps_filter = f"fps=1/{interval_sec}"

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vf", fps_filter,
        "-q:v", str(quality),
        pattern,
    ]

    logger.debug("Running ffmpeg snapshot extraction: %s", " ".join(cmd))

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise SnapshotExtractionError(
            f"ffmpeg snapshot extraction failed (returncode={proc.returncode}): "
            f"{stderr.decode(errors='replace')}"
        )

    snapshots = sorted(output_dir.glob(f"*.{output_format}"))

    if not snapshots:
        raise SnapshotExtractionError(
            f"No snapshots were extracted from: {video_path.name}"
        )

    # max_snapshots 制限：超過分を削除して切り捨て
    if max_snapshots is not None and len(snapshots) > max_snapshots:
        for excess in snapshots[max_snapshots:]:
            excess.unlink(missing_ok=True)
        snapshots = snapshots[:max_snapshots]

    logger.info(
        "Snapshots extracted: count=%d  interval=%.1fs  dir=%s",
        len(snapshots), interval_sec, output_dir,
    )
    return snapshots
