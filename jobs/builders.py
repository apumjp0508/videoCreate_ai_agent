"""
Workflow に渡す Pipeline Input を組み立てるビルダー。

設計:
  PipelineInputBuilderProtocol  ─ インターフェース（Protocol）
  VideoPipelineInputBuilder     ─ VideoPipelineWorkflow 用の具体的な実装
  PipelineInputBuildError       ─ 組み立て失敗時の例外

Workflow の種類が増えたときは:
  1. 対応する Input Builder をここに追加する（PipelineInputBuilderProtocol を実装）
  2. start_workflow_for_job に新しい builder インスタンスを渡す

例:
  # 将来の別 Workflow 用に差し替える場合
  builder = SomeOtherPipelineInputBuilder()
  start_workflow_for_job(job, builder=builder)
"""
from __future__ import annotations

import uuid
from typing import Any, Protocol

from jobs.models import AssetRole, VideoJob
from temporal.pipeline_types import PipelineInput


# ─────────────────────────────────────────────────────────────
# 例外
# ─────────────────────────────────────────────────────────────

class PipelineInputBuildError(Exception):
    """PipelineInput の組み立てに必要なデータが不足している場合。"""


# ─────────────────────────────────────────────────────────────
# インターフェース（Protocol）
# ─────────────────────────────────────────────────────────────

class PipelineInputBuilderProtocol(Protocol):
    """
    VideoJob から Workflow への入力を組み立てるインターフェース。

    Workflow の種類が増えるたびにこのプロトコルを実装した
    新しいビルダーを追加するだけでよく、呼び出し側（services.py）は変更不要。
    """

    def build(self, job: VideoJob) -> Any:
        """
        VideoJob を受け取り、対応する Workflow の Input を返す。

        Raises:
            PipelineInputBuildError: 組み立てに必要なデータが不足している場合
        """
        ...


# ─────────────────────────────────────────────────────────────
# 具体的なビルダー実装
# ─────────────────────────────────────────────────────────────

class VideoPipelineInputBuilder:
    """
    VideoPipelineWorkflow 用の PipelineInput を組み立てるビルダー。

    各フィールドの取得元:
      job_id             → str(job.id)
      request_id         → uuid.uuid4()（冪等キー、呼び出しごとに生成）
      user_id            → job.user_id
      video_ai_config_id → job.video_ai_config_id
      prompt_id          → job.prompt_id（prompts テーブルの PK）
      image_ids          → assets で role=MAIN_IMAGE のものを収集
      audio_ids          → assets で role=BGM のものを収集
      oauth_record_id    → youtube_channel → user_google_account → oauth_token.id
      youtube_channel_id → channel.youtube_channel_id（YouTube API のチャンネル ID 文字列）
      publish_mode       → job.publish_mode

    Raises:
        PipelineInputBuildError: prompt_id / youtube_channel が未設定の場合
    """

    def build(self, job: VideoJob) -> PipelineInput:
        if job.prompt_id is None:
            raise PipelineInputBuildError(
                f"job.prompt が未設定です  job_id={job.id}"
            )
        if job.youtube_channel_id is None:
            raise PipelineInputBuildError(
                f"job.youtube_channel が未設定です  job_id={job.id}"
            )

        # oauth_token まで含めて一括取得し、lazy クエリを防ぐ
        from google_auth.models import YoutubeChannel
        channel = (
            YoutubeChannel.objects
            .select_related('user_google_account__oauth_token')
            .get(pk=job.youtube_channel_id)
        )
        oauth_record_id = self._get_oauth_record_id(channel)

        assets = job.assets.all()
        image_ids = [a.asset_id for a in assets if a.asset_role == AssetRole.MAIN_IMAGE]
        audio_ids  = [a.asset_id for a in assets if a.asset_role == AssetRole.BGM]

        return PipelineInput(
            job_id=str(job.id),
            request_id=str(uuid.uuid4()),
            user_id=job.user_id,
            credential_id=job.credential_id or 0,
            model_id=job.model_id or 0,
            prompt_id=job.prompt_id,
            image_ids=image_ids,
            audio_ids=audio_ids,
            oauth_record_id=oauth_record_id,
            youtube_channel_id=channel.youtube_channel_id,
            publish_mode=job.publish_mode,
        )

    def _get_oauth_record_id(self, channel) -> int:
        """チャンネルに紐づく OauthToken の id を返す。未取得なら 0。"""
        from google_auth.models import OauthToken
        try:
            return channel.user_google_account.oauth_token.id
        except OauthToken.DoesNotExist:
            return 0
