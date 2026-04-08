"""
JobProgress Activity の Django 実装。

update_job_progress の処理:
  1. VideoJob.current_step を input.step に更新する
  2. input.status が指定されていれば VideoJob.status も更新する
  3. VideoJobEvent を追記する（イベントソーシング的に削除・更新はしない）

worker_pipeline.py での差し替え方:
    from temporal.activities.job_progress import dummy as jp_dummy
    from temporal.activities.job_progress.django_service import DjangoJobProgressService
    jp_dummy._service = DjangoJobProgressService()
"""
from __future__ import annotations

import logging

from asgiref.sync import sync_to_async

from temporal.activities.job_progress.interfaces import (
    UpdateJobProgressInput,
    UpdateJobProgressOutput,
)

logger = logging.getLogger(__name__)


class DjangoJobProgressService:
    """
    VideoJob.current_step と VideoJobEvent を Django ORM で更新するサービス。
    """

    async def update_job_progress(
        self,
        input: UpdateJobProgressInput,
    ) -> UpdateJobProgressOutput:
        logger.info(
            "update_job_progress  job_id=%s  step=%s  event=%s  status=%s",
            input.job_id, input.step, input.event_type,
            input.status or "(no change)",
        )
        await sync_to_async(self._update_sync)(input)
        return UpdateJobProgressOutput(success=True)

    @staticmethod
    def _update_sync(input: UpdateJobProgressInput) -> None:
        from jobs.models import VideoJob, VideoJobEvent

        # ── VideoJob.current_step（+ 任意で status）を更新 ────────
        update_kwargs: dict = {"current_step": input.step}
        update_fields = ["current_step", "updated_at"]

        if input.status:
            update_kwargs["status"] = input.status
            update_fields.append("status")

        VideoJob.objects.filter(id=int(input.job_id)).update(**update_kwargs)

        # ── VideoJobEvent を追記 ──────────────────────────────────
        VideoJobEvent.objects.create(
            job_id=int(input.job_id),
            event_type=input.event_type,
            step_name=input.step,
            message=input.message or f"ステップ更新: {input.step}",
            payload_json=input.payload or {},
        )

        logger.debug(
            "update_job_progress done  job_id=%s  step=%s",
            input.job_id, input.step,
        )
