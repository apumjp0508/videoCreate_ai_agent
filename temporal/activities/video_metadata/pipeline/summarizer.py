"""
OpenAI GPT API を使って文字起こしテキストを要約・トピック抽出するユーティリティ。

Temporal / Django に依存しない独立モジュール。
単体テストや別サービスからも直接利用できる。

使い方:
    from temporal.activities.video_metadata.pipeline.summarizer import summarize_transcript

    result = await summarize_transcript(transcript_text, api_key="sk-...")
    print(result["summary"])
    print(result["topics"])
"""
from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
あなたは動画コンテンツ分析の専門家です。
与えられた動画の文字起こしテキストを分析し、以下の2点を抽出してください。

1. **要約**: 動画の内容を3〜5文で簡潔にまとめてください。
2. **主要トピック**: 動画で扱われている主なテーマや話題を3〜5個のキーワードで挙げてください。

必ず下記の JSON 形式のみで返してください（説明文・前置きは不要）:
{
  "summary": "要約テキスト",
  "topics": ["トピック1", "トピック2", "トピック3"]
}\
"""


class SummarizationError(Exception):
    """OpenAI GPT API による要約・解析に失敗した場合。"""


async def summarize_transcript(
    transcript: str,
    *,
    api_key: str,
    model: str = "gpt-4o-mini",
    language: str = "ja",
    max_tokens: int = 1000,
    system_prompt: str = _SYSTEM_PROMPT,
) -> dict[str, str | list[str]]:
    """
    文字起こしテキストを GPT に投げて要約とトピックを取得する。

    Args:
        transcript:    Whisper などで得た文字起こしテキスト
        api_key:       OpenAI API キー
        model:         GPT モデル名（デフォルト: gpt-4o-mini）
        language:      要約の出力言語コード（"ja" / "en" 等）
        max_tokens:    レスポンスの最大トークン数
        system_prompt: カスタムシステムプロンプト（省略時はデフォルト）

    Returns:
        {"summary": str, "topics": list[str]}

    Raises:
        SummarizationError: API エラーまたは JSON パース失敗の場合
    """
    import openai

    logger.info(
        "Summarizing transcript: %d chars  model=%s  language=%s",
        len(transcript), model, language,
    )

    lang_hint = f"（{language} 言語で回答してください）" if language != "ja" else ""
    user_message = (
        f"以下の文字起こしを分析してください{lang_hint}。\n\n"
        f"---\n{transcript}\n---"
    )

    client = openai.AsyncOpenAI(api_key=api_key)

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
    except openai.OpenAIError as exc:
        raise SummarizationError(f"GPT API error: {exc}") from exc

    raw = response.choices[0].message.content or ""

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SummarizationError(
            f"Failed to parse GPT response as JSON: {raw!r}"
        ) from exc

    summary: str = data.get("summary", "")
    topics: list[str] = data.get("topics", [])

    logger.info(
        "Summarization complete: summary=%d chars  topics=%s",
        len(summary), topics,
    )
    return {"summary": summary, "topics": topics}
