"""
ダミー Activity 群。
本番実装に置き換えるまでの骨組み確認用。

各 Activity は後で以下に差し替える:
  generate_video_script  -> LLM でスクリプト生成
  generate_video         -> 動画生成 API 呼び出し
  upload_to_youtube      -> YouTube Data API アップロード
"""
import asyncio
import logging

from temporalio import activity

logger = logging.getLogger(__name__)


@activity.defn
async def generate_video_script(job_id: str, prompt: str) -> str:
    """スクリプト生成 (ダミー: 即時返却)"""
    logger.info("[Activity] generate_video_script job_id=%s", job_id)
    await asyncio.sleep(0.1)  # 本番では LLM API 呼び出し
    return f"[DUMMY SCRIPT] job_id={job_id} prompt={prompt}"


@activity.defn
async def generate_video(job_id: str, script: str) -> str:
    """動画生成 (ダミー: フェイク URL を返す)"""
    logger.info("[Activity] generate_video job_id=%s", job_id)
    await asyncio.sleep(0.1)  # 本番では動画生成 API 呼び出し
    return f"https://storage.example.com/videos/{job_id}.mp4"


@activity.defn
async def upload_to_youtube(job_id: str, video_url: str) -> str:
    """YouTube アップロード (ダミー: フェイク video_id を返す)"""
    logger.info("[Activity] upload_to_youtube job_id=%s video_url=%s", job_id, video_url)
    await asyncio.sleep(0.1)  # 本番では YouTube Data API 呼び出し
    return f"dummy_yt_{job_id[:8]}"
