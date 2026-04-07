"""
OpenAI Whisper API を使って音声ファイルを文字起こしするユーティリティ。

Temporal / Django に依存しない独立モジュール。
単体テストや別サービスからも直接利用できる。

使い方:
    from temporal.activities.video_metadata.pipeline.transcriber import transcribe_audio

    text = await transcribe_audio(audio_path, api_key="sk-...")
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Whisper API が受け付けるファイルサイズ上限（25 MB）
_WHISPER_MAX_BYTES = 25 * 1024 * 1024


class TranscriptionError(Exception):
    """OpenAI Whisper API による文字起こしに失敗した場合。"""


async def transcribe_audio(
    audio_path: str | Path,
    *,
    api_key: str,
    model: str = "whisper-1",
    language: str | None = None,
    prompt: str | None = None,
) -> str:
    """
    OpenAI Whisper API に音声を送信して文字起こしテキストを返す。

    Args:
        audio_path: 音声ファイルのパス（mp3 / wav / m4a / mp4 / webm 等）
        api_key:    OpenAI API キー
        model:      Whisper モデル名（現時点では "whisper-1" のみ）
        language:   音声の言語コード（"ja" / "en" 等）。None で自動検出
        prompt:     Whisper へのコンテキストヒント（専門用語などを含めると精度向上）

    Returns:
        文字起こしテキスト

    Raises:
        TranscriptionError: ファイルサイズ超過・API エラーなどの場合
    """
    import openai

    audio_path = Path(audio_path)

    # ファイルサイズチェック
    size_bytes = audio_path.stat().st_size
    if size_bytes > _WHISPER_MAX_BYTES:
        raise TranscriptionError(
            f"Audio file too large for Whisper API: {size_bytes} bytes "
            f"(limit: {_WHISPER_MAX_BYTES} bytes). "
            "Consider splitting the audio before transcribing."
        )

    logger.info(
        "Transcribing audio: %s  model=%s  language=%s  size=%d bytes",
        audio_path.name, model, language or "auto", size_bytes,
    )

    client = openai.AsyncOpenAI(api_key=api_key)

    try:
        with open(audio_path, "rb") as audio_file:
            kwargs: dict = {
                "model": model,
                "file": audio_file,
                "response_format": "text",
            }
            if language:
                kwargs["language"] = language
            if prompt:
                kwargs["prompt"] = prompt

            transcript = await client.audio.transcriptions.create(**kwargs)

    except openai.OpenAIError as exc:
        raise TranscriptionError(f"Whisper API error: {exc}") from exc

    # response_format="text" の場合は str が返る
    result: str = transcript if isinstance(transcript, str) else transcript.text

    logger.info("Transcription complete: %d characters", len(result))
    return result
