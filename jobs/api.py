"""
jobs アプリの REST API ビュー。

エンドポイント:
  GET /api/jobs/<job_id>/status/
    ─ VideoJob の現在の状態と直近イベントログを返す

認証:
  ログインユーザーが自分の job のみ取得可能。
  未ログインは 401、他人の job は 404 を返す。

レスポンス例:
  {
    "job_id": 42,
    "status": "generating",
    "status_display": "動画生成中",
    "current_step": "WAIT_AI_RESULT",
    "current_step_display": "AI生成待ち",
    "temporal_workflow_id": "42",
    "started_at": "2026-04-08T10:00:00Z",
    "updated_at": "2026-04-08T10:05:00Z",
    "completed_at": null,
    "youtube_video_id": "",
    "youtube_video_url": "",
    "error_code": "",
    "error_message": "",
    "events": [
      {
        "event_type": "WORKFLOW_STARTED",
        "event_type_display": "Workflow開始",
        "step_name": "",
        "message": "Workflow started  id=42",
        "payload": {},
        "created_at": "2026-04-08T10:00:01Z"
      }
    ]
  }
"""
from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from jobs.models import EventType, JobStatus, JobStep, VideoJob


@require_GET
@login_required
def job_status(request, job_id: int) -> JsonResponse:
    """
    GET /api/jobs/<job_id>/status/

    VideoJob の現在状態と直近 50 件のイベントログを返す。

    Errors:
      401 : 未ログイン
      404 : job が存在しないか他のユーザーの job
    """
    try:
        job = (
            VideoJob.objects
            .prefetch_related("events")
            .get(id=job_id, user=request.user)
        )
    except VideoJob.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    # ── current_step の表示名を解決 ───────────────────────────
    step_display = dict(JobStep.choices).get(job.current_step, job.current_step)
    status_display = dict(JobStatus.choices).get(job.status, job.status)
    event_type_display_map = dict(EventType.choices)

    # ── 直近 50 件のイベントを時系列順で取得 ─────────────────
    events = [
        {
            "event_type":         e.event_type,
            "event_type_display": event_type_display_map.get(e.event_type, e.event_type),
            "step_name":          e.step_name,
            "message":            e.message,
            "payload":            e.payload_json or {},
            "created_at":         e.created_at.isoformat(),
        }
        for e in job.events.order_by("created_at")[:50]
    ]

    data = {
        "job_id":               job.id,
        "status":               job.status,
        "status_display":       status_display,
        "current_step":         job.current_step,
        "current_step_display": step_display,
        "temporal_workflow_id": job.temporal_workflow_id,
        "started_at":           job.started_at.isoformat() if job.started_at else None,
        "updated_at":           job.updated_at.isoformat(),
        "completed_at":         job.completed_at.isoformat() if job.completed_at else None,
        "youtube_video_id":     job.youtube_video_id,
        "youtube_video_url":    job.youtube_video_url,
        "error_code":           job.error_code,
        "error_message":        job.error_message,
        "events":               events,
    }

    return JsonResponse(data)
