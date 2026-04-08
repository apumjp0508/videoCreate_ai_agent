"""
OpenAI GPT-4o Vision を使った ThumbnailGenerationServiceProtocol の本番実装。

generate_thumbnail の処理フロー:
  1. 動画 URL から動画を一時ファイルにダウンロード（httpx）
  2. ffmpeg で 1 秒ごとのスナップショットを抽出   → pipeline.snapshot_extractor
  3. GPT-4o Vision で各スナップショットをスコアリング → pipeline.snapshot_scorer
  4. 最高スコアのスナップショットを選択（同点の場合はランダム）
  5. 選択画像を永続的な一時ファイルとして保存し file:// URL を返す

worker_pipeline.py での差し替え方:
    from temporal.activities.thumbnail_generation import dummy as th_dummy
    from temporal.activities.thumbnail_generation.openai_service import OpenAIThumbnailService
    th_dummy._service = OpenAIThumbnailService()

必要な環境変数:
    OPENAI_API_KEY : OpenAI API キー

必要なシステム依存:
    ffmpeg : PATH が通っていること
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import tempfile
from pathlib import Path

from temporal.activities.thumbnail_generation.interfaces import (
    GenerateThumbnailInput,
    GenerateThumbnailOutput,
)
from temporal.activities.thumbnail_generation.pipeline.snapshot_extractor import (
    SnapshotExtractionError,
    extract_snapshots,
)
from temporal.activities.thumbnail_generation.pipeline.snapshot_scorer import (
    SnapshotScoringError,
    score_snapshots,
)

logger = logging.getLogger(__name__)


class OpenAIThumbnailService:
    """
    GPT-4o Vision を使ったサムネイル選択サービス。

    動画から 1 秒ごとのスナップショットを抽出し、GPT-4o Vision が
    サムネイルとして最も適した 1 枚をスコアリングで選択する。

    Attributes:
        api_key:              OpenAI API キー（省略時は OPENAI_API_KEY 環境変数）
        gpt_model:            GPT Vision モデル（デフォルト: gpt-4o）
        snapshot_interval_sec: スナップショット抽出間隔（秒）
        max_snapshots:        GPT に送る最大スナップショット数
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        gpt_model: str = "gpt-4o",
        snapshot_interval_sec: float = 1.0,
        max_snapshots: int = 30,
    ) -> None:
        self._api_key = api_key or os.environ["OPENAI_API_KEY"]
        self._gpt_model = gpt_model
        self._snapshot_interval_sec = snapshot_interval_sec
        self._max_snapshots = max_snapshots

    # ─────────────────────────────────────────────────────────────
    # generate_thumbnail
    # ─────────────────────────────────────────────────────────────

    async def generate_thumbnail(
        self,
        input: GenerateThumbnailInput,
    ) -> GenerateThumbnailOutput:
        """
        動画 URL → スナップショット抽出 → GPT スコアリング → サムネイル選択。

        各ステップで発生した例外はそのまま上位に伝播し、
        Temporal が Activity のリトライを制御する。
        一時ファイル（動画・不採用スナップショット）はエラー時も必ず削除される。
        選択されたサムネイルは永続的な一時ファイルとして保存し file:// URL で返す。
        """
        logger.info(
            "generate_thumbnail  job_id=%s  url=%s  model=%s",
            input.job_id, input.video_url, self._gpt_model,
        )

        video_path = await self._download_video(input.video_url)
        snapshots: list[Path] = []
        selected: Path | None = None

        try:
            # Step 1: ffmpeg でスナップショット抽出
            logger.info(
                "[job=%s] Step 1/2 - Extracting snapshots via ffmpeg"
                "  interval=%.1fs  max=%s",
                input.job_id, self._snapshot_interval_sec, self._max_snapshots,
            )
            snapshots = await extract_snapshots(
                video_path,
                interval_sec=self._snapshot_interval_sec,
                max_snapshots=self._max_snapshots,
            )

            # Step 2: GPT-4o Vision でスコアリング & 選択
            logger.info(
                "[job=%s] Step 2/2 - Scoring %d snapshots via GPT Vision",
                input.job_id, len(snapshots),
            )
            selected = await score_snapshots(
                snapshots,
                video_summary=input.video_summary,
                title=input.title,
                api_key=self._api_key,
                model=self._gpt_model,
            )

            # 選択したスナップショットを永続的な一時ファイルにコピー
            thumbnail_path = await self._persist_thumbnail(selected, input.job_id)
            thumbnail_url = thumbnail_path.as_uri()   # file:///tmp/thumbnail_<job>_xxx.jpg

        except (SnapshotExtractionError, SnapshotScoringError):
            raise   # Temporal に伝播させてリトライを任せる
        finally:
            video_path.unlink(missing_ok=True)
            # 不採用スナップショットを削除（selected は呼び出し元が管理）
            for snap in snapshots:
                if snap != selected:
                    snap.unlink(missing_ok=True)
            # 空になったスナップショットディレクトリを削除
            if snapshots:
                try:
                    snapshots[0].parent.rmdir()
                except OSError:
                    pass

        logger.info(
            "generate_thumbnail complete  job_id=%s  thumbnail_url=%s",
            input.job_id, thumbnail_url,
        )

        return GenerateThumbnailOutput(
            thumbnail_url=thumbnail_url,
            metadata={
                "generated_by": "openai_gpt_vision",
                "model": self._gpt_model,
                "snapshot_count_evaluated": len(snapshots),
            },
        )

    # ─────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    async def _persist_thumbnail(selected: Path, job_id: str) -> Path:
        """
        選択されたスナップショットを永続的な一時ファイルとして保存する。

        返り値のパスは set_thumbnail Activity が消費するまで保持される。
        cleanup はワークフロー完了後に OS の tmp クリーンアップに任せる。
        """
        suffix = selected.suffix or ".jpg"
        tmp = tempfile.NamedTemporaryFile(
            prefix=f"thumbnail_{job_id}_",
            suffix=suffix,
            delete=False,
        )
        tmp.close()
        dest = Path(tmp.name)
        await asyncio.to_thread(shutil.copy2, selected, dest)
        logger.debug("Thumbnail persisted: %s", dest)
        return dest

    @staticmethod
    async def _download_video(url: str) -> Path:
        """
        動画 URL から一時ファイルにストリーミングダウンロードして返す。
        返り値のパスは呼び出し元で必ず削除すること。
        """
        import httpx

        suffix = Path(url.split("?")[0]).suffix or ".mp4"
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.close()
        output_path = Path(tmp.name)

        logger.info("Downloading video: %s", url)

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=300.0) as client:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    with open(output_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
        except Exception:
            output_path.unlink(missing_ok=True)
            raise

        size_bytes = output_path.stat().st_size
        logger.info(
            "Video downloaded: %s  size=%d bytes", output_path.name, size_bytes
        )
        return output_path
