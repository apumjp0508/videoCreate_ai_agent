"""
VideoMetadata サービス層の Protocol（抽象インターフェース）定義。

設計意図:
  - Activity 関数はこの Protocol に準拠したサービスオブジェクトに処理を委譲する
  - 外部 AI プロバイダー（Claude / GPT / Gemini など）が変わっても
    Workflow / Activity 層を変えずにサービス実装だけ差し替えられる
  - YouTube / TikTok など投稿先プラットフォームを意識せず、
    「動画からメタ情報を生成する」という責務だけを持つ

使い方:
  1. この Protocol を実装するクラスを作る（DummyVideoMetadataService など）
  2. dummy.py や本番 activities.py から _service として参照する
  3. worker_pipeline.py で差し替える
"""
from __future__ import annotations

from typing import Protocol

from temporal.activities.video_metadata.interfaces import (
    AnalyzeVideoContentInput,
    AnalyzeVideoContentOutput,
    GenerateVideoMetadataInput,
    GenerateVideoMetadataOutput,
)


class VideoMetadataServiceProtocol(Protocol):
    """
    動画メタ情報生成に必要な処理を担うサービスの契約。

    実装クラスは外部 AI（Claude / GPT / Gemini 等）の呼び出しを行う。
    YouTube 固有の概念（category_id など）は持たない。
    """

    async def analyze_video_content(
        self,
        input: AnalyzeVideoContentInput,
    ) -> AnalyzeVideoContentOutput:
        """
        動画を外部 AI に送信して要約とトピックを取得する。

        実装例:
          - 動画URLから動画をダウンロードし、マルチモーダル AI に送信
          - AI が返した要約テキストと検出トピックを返す
        """
        ...

    async def generate_video_metadata(
        self,
        input: GenerateVideoMetadataInput,
    ) -> GenerateVideoMetadataOutput:
        """
        動画要約と生成プロンプトを外部 AI に送信し、
        タイトル・説明・タグ・カテゴリを生成して返す。

        実装例:
          - summary + prompt_text をプロンプトに組み込んで AI に送信
          - AI が返した JSON をパースして GenerateVideoMetadataOutput に詰める
        """
        ...
