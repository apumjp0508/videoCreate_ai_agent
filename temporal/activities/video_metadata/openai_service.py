"""
OpenAI (Whisper + GPT) を使った VideoMetadataServiceProtocol の本番実装。

analyze_video_content の処理フロー:
  1. 動画 URL から動画を一時ファイルにダウンロード（httpx）
  2. ffmpeg で音声を抽出           → pipeline.audio_extractor
  3. OpenAI Whisper で文字起こし   → pipeline.transcriber
  4. OpenAI GPT で要約・トピック抽出 → pipeline.summarizer
  5. AnalyzeVideoContentOutput を返す

generate_video_metadata の処理フロー:
  1. 動画要約 + プロンプトを GPT に投げてメタデータを生成
  2. GenerateVideoMetadataOutput を返す

worker_pipeline.py での差し替え方:
    from temporal.activities.video_metadata import dummy as vm_dummy
    from temporal.activities.video_metadata.openai_service import OpenAIVideoMetadataService
    vm_dummy._service = OpenAIVideoMetadataService()

必要な環境変数:
    OPENAI_API_KEY : OpenAI API キー

必要なシステム依存:
    ffmpeg : PATH が通っていること
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

from temporal.activities.video_metadata.interfaces import (
    AnalyzeVideoContentInput,
    AnalyzeVideoContentOutput,
    GenerateVideoMetadataInput,
    GenerateVideoMetadataOutput,
)
from temporal.activities.video_metadata.pipeline.audio_extractor import (
    AudioExtractionError,
    extract_audio_from_video,
)
from temporal.activities.video_metadata.pipeline.summarizer import (
    SummarizationError,
    summarize_transcript,
)
from temporal.activities.video_metadata.pipeline.transcriber import (
    TranscriptionError,
    transcribe_audio,
)

logger = logging.getLogger(__name__)

_METADATA_SYSTEM_PROMPT = """\
あなたは YouTube 動画のメタデータ生成の専門家です。
与えられた動画の要約と生成プロンプトをもとに、YouTube 向けのメタデータを生成してください。

必ず下記の JSON 形式のみで返してください（説明文・前置きは不要）:
{
  "title": "クリックされやすい動画タイトル（60文字以内）",
  "description": "動画の説明文（3〜5段落、改行あり）",
  "tags": ["タグ1", "タグ2", ...（最大15個）],
  "category": "Education または Entertainment または HowTo または Science または News のいずれか"
}\
"""


class OpenAIVideoMetadataService:
    """
    OpenAI Whisper + GPT を使った動画メタデータ生成サービス。

    Attributes:
        api_key:        OpenAI API キー（省略時は OPENAI_API_KEY 環境変数を使用）
        whisper_model:  Whisper モデル（デフォルト: whisper-1）
        gpt_model:      GPT モデル（デフォルト: gpt-4o-mini）
        language:       Whisper の音声言語コード（None で自動検出）
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        whisper_model: str = "whisper-1",
        gpt_model: str = "gpt-4o-mini",
        language: str | None = None,
    ) -> None:
        self._api_key = api_key or os.environ["OPENAI_API_KEY"]
        self._whisper_model = whisper_model
        self._gpt_model = gpt_model
        self._language = language

    # ─────────────────────────────────────────────────────────────
    # analyze_video_content
    # ─────────────────────────────────────────────────────────────

    async def analyze_video_content(
        self,
        input: AnalyzeVideoContentInput,
    ) -> AnalyzeVideoContentOutput:
        """
        動画 URL → 音声抽出 → 文字起こし → 要約 の一連処理を実行する。

        各ステップで発生した例外はそのまま上位に伝播し、
        Temporal が Activity のリトライを制御する。
        一時ファイルはエラー時も必ず削除される。
        """
        logger.info(
            "analyze_video_content  job_id=%s  url=%s",
            input.job_id, input.video_url,
        )

        video_path = await self._download_video(input.video_url)
        audio_path: Path | None = None

        try:
            # Step 1: ffmpeg で音声抽出
            logger.info("[job=%s] Step 1/3 - Extracting audio via ffmpeg", input.job_id)
            audio_path = await extract_audio_from_video(video_path)

            # Step 2: Whisper で文字起こし
            logger.info("[job=%s] Step 2/3 - Transcribing audio via Whisper", input.job_id)
            transcript = await transcribe_audio(
                audio_path,
                api_key=self._api_key,
                model=self._whisper_model,
                language=self._language,
            )

            # Step 3: GPT で要約・トピック抽出
            logger.info("[job=%s] Step 3/3 - Summarizing via GPT", input.job_id)
            result = await summarize_transcript(
                transcript,
                api_key=self._api_key,
                model=self._gpt_model,
            )

        except (AudioExtractionError, TranscriptionError, SummarizationError):
            raise  # Temporal に伝播させてリトライを任せる
        finally:
            video_path.unlink(missing_ok=True)
            if audio_path is not None:
                audio_path.unlink(missing_ok=True)

        logger.info(
            "analyze_video_content complete  job_id=%s  summary_len=%d  topics=%s",
            input.job_id, len(result["summary"]), result["topics"],
        )

        return AnalyzeVideoContentOutput(
            summary=result["summary"],
            detected_topics=result["topics"],
        )

    # ─────────────────────────────────────────────────────────────
    # generate_video_metadata
    # ─────────────────────────────────────────────────────────────

    async def generate_video_metadata(
        self,
        input: GenerateVideoMetadataInput,
    ) -> GenerateVideoMetadataOutput:
        """
        動画要約とプロンプトから GPT を使って YouTube メタデータを生成する。
        """
        import openai

        logger.info(
            "generate_video_metadata  job_id=%s  lang=%s",
            input.job_id, input.language,
        )

        lang_note = f"（言語: {input.language}）" if input.language != "ja" else ""
        user_message = (
            f"以下の情報をもとに YouTube 動画のメタデータを生成してください{lang_note}。\n\n"
            f"■ 動画の要約:\n{input.video_summary}\n\n"
            f"■ 生成プロンプト:\n{input.prompt_text}"
        )

        client = openai.AsyncOpenAI(api_key=self._api_key)

        try:
            response = await client.chat.completions.create(
                model=self._gpt_model,
                messages=[
                    {"role": "system", "content": _METADATA_SYSTEM_PROMPT},
                    {"role": "user",   "content": user_message},
                ],
                max_tokens=1500,
                response_format={"type": "json_object"},
            )
        except openai.OpenAIError as exc:
            logger.error("GPT API error in generate_video_metadata: %s", exc)
            raise

        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)

        logger.info(
            "generate_video_metadata complete  job_id=%s  title=%r",
            input.job_id, data.get("title", ""),
        )

        return GenerateVideoMetadataOutput(
            title=data.get("title", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            category=data.get("category", "Entertainment"),
        )

    # ─────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────

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
