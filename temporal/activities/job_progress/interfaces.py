"""
JobProgress Activity のインターフェース定義。

Workflow はここだけを参照する。実装（dummy / 本番）は一切知らない。

責務:
  Workflow の各ステップ完了時に Django 側の VideoJob.current_step と
  VideoJobEvent を更新する。動画生成 / YouTube 投稿の進捗を Django 側に伝播させる。

ルール:
  - Activity は専用の Input / Output dataclass を持つ
  - Activity スタブ関数は raise NotImplementedError のみ
  - 実装ファイルは @activity.defn(name="<同じ名前>") で同一名を登録すること

Activity 一覧:
  1. update_job_progress  ─ VideoJob.current_step / VideoJobEvent を更新
"""
from __future__ import annotations

from dataclasses import dataclass, field

from temporalio import activity


# ─────────────────────────────────────────────────────────────
# 1. update_job_progress  ─ 進捗更新
# ─────────────────────────────────────────────────────────────

@dataclass
class UpdateJobProgressInput:
    """
    VideoJob の進捗情報を Django 側に書き込むための入力。

    job_id      : 対象 VideoJob の PK（文字列）
    step        : jobs.models.JobStep の値（例: "CALL_AI"）
    event_type  : jobs.models.EventType の値（例: "AI_REQUEST_SENT"）
    message     : VideoJobEvent に記録するメッセージ
    payload     : VideoJobEvent.payload_json に記録する追加情報
    status      : jobs.models.JobStatus の値（空文字 = 更新しない）
                  ステータス遷移が必要な場合にのみ指定する。
                  例: YouTube 投稿開始時に "publishing" を指定する
    """
    job_id: str
    step: str
    event_type: str
    message: str = ""
    payload: dict = field(default_factory=dict)
    status: str = ""   # 空文字 = JobStatus を変更しない


@dataclass
class UpdateJobProgressOutput:
    success: bool = True


@activity.defn
async def update_job_progress(
    input: UpdateJobProgressInput,
) -> UpdateJobProgressOutput:
    raise NotImplementedError
