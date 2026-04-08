"""
JobProgress Activity のダミー実装。

DummyJobProgressService はログだけ出して何もしない no-op 実装。
テスト環境や Temporal Worker の動作確認に使う。

本番では worker_pipeline.py で:
    from temporal.activities.job_progress import dummy as jp_dummy
    from temporal.activities.job_progress.django_service import DjangoJobProgressService
    jp_dummy._service = DjangoJobProgressService()
と差し替える。
"""
import logging

from temporalio import activity

from temporal.activities.job_progress.interfaces import (
    UpdateJobProgressInput,
    UpdateJobProgressOutput,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# ダミーサービス実装
# ─────────────────────────────────────────────────────────────

class DummyJobProgressService:
    """
    進捗更新の no-op 実装。
    DB 操作は行わず、ログ出力のみ。
    """

    async def update_job_progress(
        self,
        input: UpdateJobProgressInput,
    ) -> UpdateJobProgressOutput:
        logger.info(
            "[Dummy] update_job_progress  job_id=%s  step=%s  event=%s  status=%s  msg=%s",
            input.job_id, input.step, input.event_type,
            input.status or "(no change)", input.message,
        )
        return UpdateJobProgressOutput(success=True)


# ─────────────────────────────────────────────────────────────
# Activity 関数（worker_pipeline.py で登録する）
# ─────────────────────────────────────────────────────────────

_service = DummyJobProgressService()


@activity.defn(name="update_job_progress")
async def dummy_update_job_progress(
    input: UpdateJobProgressInput,
) -> UpdateJobProgressOutput:
    return await _service.update_job_progress(input)
