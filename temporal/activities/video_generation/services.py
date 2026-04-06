"""
VideoGeneration サービス層の Protocol（抽象インターフェース）定義。

設計意図:
  - Activity 関数はこの Protocol に準拠したサービスオブジェクトに処理を委譲する
  - サービスを差し替えることで Activity 実装ごと変えなくてもよい
  - テスト時はモックサービスを差し込める
  - AI プロバイダーが変わっても Workflow / Activity 層を変えずに済む

使い方:
  1. この Protocol を実装するクラスを作る（DummyVideoGenerationService など）
  2. dummy.py や本番 activities.py から _service として参照する
  3. 将来 provider ごとに実装クラスを作り worker.py で差し替える

NOTE: Protocol は抽象基底クラスではないため継承不要。
      メソッドシグネチャが一致していれば自動的に準拠とみなされる（構造的部分型）。
"""
from __future__ import annotations

from typing import Any, Protocol

from temporal.activities.video_generation.interfaces import (
    BuildAiRequestInput,
    BuildAiRequestOutput,
    FetchAiConfigInput,
    FetchAiConfigOutput,
    FetchGeneratedVideoInput,
    FetchGeneratedVideoOutput,
    FetchMaterialsInput,
    FetchMaterialsOutput,
    FetchRequestDefinitionInput,
    FetchRequestDefinitionOutput,
    PollGenerationStatusInput,
    PollGenerationStatusOutput,
    SubmitAiRequestInput,
    SubmitAiRequestOutput,
)


class VideoGenerationServiceProtocol(Protocol):
    """
    動画生成に必要なすべての処理を担うサービスの契約。
    Activity 実装はこの Protocol に依存する。
    """

    async def fetch_materials(
        self, input: FetchMaterialsInput
    ) -> FetchMaterialsOutput:
        """DB / ストレージから素材情報を取得する。"""
        ...

    async def fetch_ai_config(
        self, input: FetchAiConfigInput
    ) -> FetchAiConfigOutput:
        """DB から AI 設定（モデル名・エンドポイント・パラメータ）を取得する。"""
        ...

    async def fetch_request_definition(
        self, input: FetchRequestDefinitionInput
    ) -> FetchRequestDefinitionOutput:
        """DB からプロンプト定義・フォーマット設定を取得する。"""
        ...

    async def build_ai_request(
        self, input: BuildAiRequestInput
    ) -> BuildAiRequestOutput:
        """取得した設定・素材からAIリクエストペイロードを組み立てる。"""
        ...

    async def submit_ai_request(
        self, input: SubmitAiRequestInput
    ) -> SubmitAiRequestOutput:
        """AI プロバイダーの API にリクエストを送信する。"""
        ...

    async def poll_generation_status(
        self, input: PollGenerationStatusInput
    ) -> PollGenerationStatusOutput:
        """生成ジョブのステータスをポーリングする。"""
        ...

    async def fetch_generated_video(
        self, input: FetchGeneratedVideoInput
    ) -> FetchGeneratedVideoOutput:
        """完成した動画の情報を取得する。"""
        ...
