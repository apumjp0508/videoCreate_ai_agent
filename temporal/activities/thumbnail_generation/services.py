"""
ThumbnailGeneration サービス層の Protocol（抽象インターフェース）定義。

設計意図:
  - Activity 関数はこの Protocol に準拠したサービスオブジェクトに処理を委譲する
  - 外部 AI プロバイダー（DALL-E / Stable Diffusion / Imagen など）が変わっても
    Workflow / Activity 層を変えずにサービス実装だけ差し替えられる
  - YouTube / TikTok など投稿先プラットフォームを意識せず、
    「メタ情報からサムネイルを生成する」という責務だけを持つ

使い方:
  1. この Protocol を実装するクラスを作る（DummyThumbnailService など）
  2. dummy.py や本番 activities.py から _service として参照する
  3. worker_pipeline.py で差し替える
"""
from __future__ import annotations

from typing import Protocol

from temporal.activities.thumbnail_generation.interfaces import (
    GenerateThumbnailInput,
    GenerateThumbnailOutput,
)


class ThumbnailGenerationServiceProtocol(Protocol):
    """
    サムネイル生成に必要な処理を担うサービスの契約。

    実装クラスは外部 AI（画像生成 API）の呼び出しを行う。
    YouTube 固有の概念（サイズ制限 2MB など）は持たない。
    プラットフォームへのアップロードは呼び出し側（Workflow）が担う。
    """

    async def generate_thumbnail(
        self,
        input: GenerateThumbnailInput,
    ) -> GenerateThumbnailOutput:
        """
        動画要約・タイトルをもとにサムネイル画像を生成する。

        実装例:
          - title + video_summary をプロンプトに組み込んで画像生成 AI に送信
          - 生成された画像を一時ストレージにアップロードしてURLを返す
          - video_url から代表フレームを抽出してテキストをオーバーレイする
        """
        ...
