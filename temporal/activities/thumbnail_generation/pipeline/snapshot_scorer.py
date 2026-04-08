"""
GPT-4o Vision を使ってスナップショットにサムネイル適合スコアを付けるユーティリティ。

Temporal / Django に依存しない独立モジュール。
単体テストや別サービスからも直接利用できる。

使い方:
    from temporal.activities.thumbnail_generation.pipeline.snapshot_scorer import (
        score_snapshots,
    )

    best = await score_snapshots(
        snapshots,
        video_summary="...",
        title="...",
        api_key="sk-...",
    )
    # best は最高スコアのスナップショット Path（同点の場合はランダム選択）
"""
from __future__ import annotations

import base64
import json
import logging
import random
from pathlib import Path

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
あなたは YouTube サムネイルの専門家です。
複数の動画スナップショットを評価し、サムネイルとしての適合スコアを付けてください。

評価基準:
- 視覚的インパクト（鮮明さ、コントラスト、色彩の豊かさ）
- 内容の代表性（動画の主題・内容を適切に表しているか）
- クリック誘引力（視聴者の興味・好奇心を引くか）
- 画質（ブレ・暗すぎ・明るすぎ・黒画面等がないか）

必ず下記の JSON 形式のみで返してください（説明文・前置きは不要）:
{
  "scores": [
    {"index": 0, "score": 7},
    {"index": 1, "score": 9}
  ]
}
スコアは 1（最低）〜 10（最高）の整数で評価してください。\
"""


class SnapshotScoringError(Exception):
    """GPT Vision によるスナップショットスコアリングに失敗した場合。"""


async def score_snapshots(
    snapshots: list[Path],
    *,
    video_summary: str,
    api_key: str,
    model: str = "gpt-4o",
    title: str = "",
) -> Path:
    """
    スナップショットリストにスコアを付けて最適なサムネイルを返す。

    GPT-4o Vision に全スナップショットを一括送信してスコアを取得し、
    最高スコアのスナップショットを返す。同点が複数ある場合はランダムに選択する。

    Args:
        snapshots:      評価対象スナップショットの Path リスト（時系列昇順）
        video_summary:  動画の要約テキスト（GPT へのコンテキストとして渡す）
        api_key:        OpenAI API キー
        model:          使用する GPT Vision モデル（デフォルト: gpt-4o）
        title:          動画タイトル（省略可）

    Returns:
        最高スコアのスナップショット Path

    Raises:
        SnapshotScoringError: API エラーまたは JSON パース失敗の場合
        ValueError:           snapshots が空の場合
    """
    import openai

    if not snapshots:
        raise ValueError("score_snapshots: snapshots must not be empty")

    if len(snapshots) == 1:
        logger.info("Only 1 snapshot available, returning it directly")
        return snapshots[0]

    logger.info(
        "Scoring %d snapshots via GPT Vision  model=%s", len(snapshots), model
    )

    # ── ユーザーメッセージを構築（テキスト + 画像群）────────────
    title_line = f"動画タイトル: {title}\n" if title else ""
    intro_text = (
        f"以下は動画のスナップショット（インデックス 0〜{len(snapshots) - 1}）です。\n\n"
        f"{title_line}"
        f"動画要約:\n{video_summary}\n\n"
        "各スナップショットにサムネイル適合スコアを付けてください。"
    )

    content: list[dict] = [{"type": "text", "text": intro_text}]

    for i, path in enumerate(snapshots):
        image_bytes = await _read_bytes_async(path)
        b64 = base64.b64encode(image_bytes).decode()
        ext = path.suffix.lstrip(".").lower()
        media_type = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{media_type};base64,{b64}",
                "detail": "low",   # トークン節約のため低解像度モードを使用
            },
        })
        content.append({"type": "text", "text": f"[スナップショット index={i}]"})

    # ── GPT Vision API 呼び出し ──────────────────────────────────
    client = openai.AsyncOpenAI(api_key=api_key)

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": content},
            ],
            max_tokens=800,
            response_format={"type": "json_object"},
        )
    except openai.OpenAIError as exc:
        raise SnapshotScoringError(f"GPT Vision API error: {exc}") from exc

    raw = response.choices[0].message.content or ""

    # ── レスポンスをパースしてスコアマップを構築 ─────────────────
    try:
        data = json.loads(raw)
        scores_list: list[dict] = data.get("scores", [])
    except json.JSONDecodeError as exc:
        raise SnapshotScoringError(
            f"Failed to parse GPT response as JSON: {raw!r}"
        ) from exc

    score_map: dict[int, int] = {}
    for item in scores_list:
        idx = item.get("index")
        score = item.get("score")
        if (
            isinstance(idx, int)
            and isinstance(score, (int, float))
            and 0 <= idx < len(snapshots)
        ):
            score_map[idx] = int(score)

    if not score_map:
        logger.warning(
            "GPT returned no valid scores (raw=%r), selecting randomly", raw
        )
        return random.choice(snapshots)

    # ── 最高スコアを持つ候補からランダムに選択 ───────────────────
    max_score = max(score_map.values())
    best_indices = [idx for idx, s in score_map.items() if s == max_score]
    selected_idx = random.choice(best_indices)

    logger.info(
        "Snapshot scoring complete: total=%d  max_score=%d  tied_candidates=%d  selected_index=%d",
        len(snapshots), max_score, len(best_indices), selected_idx,
    )

    return snapshots[selected_idx]


# ── 内部ユーティリティ ────────────────────────────────────────────

async def _read_bytes_async(path: Path) -> bytes:
    """ファイルを非同期スレッドで読み込む。"""
    import asyncio
    return await asyncio.to_thread(path.read_bytes)
