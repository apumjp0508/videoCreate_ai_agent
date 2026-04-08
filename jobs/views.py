"""
jobs アプリのビュー。

ページ一覧:
  JobHistoryView  GET /dashboard/jobs/          ─ 生成履歴一覧
  JobDetailView   GET /dashboard/jobs/<id>/     ─ Job 詳細・進捗
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views import View

from jobs.models import JobStep, VideoJob

# ステップ進捗バーに表示する順序付きリスト
_STEP_ORDER = [
    (JobStep.FETCH_ASSETS,    "素材取得"),
    (JobStep.FETCH_AI_CONFIG, "AI設定"),
    (JobStep.CALL_AI,         "AI呼び出し"),
    (JobStep.WAIT_AI_RESULT,  "AI生成待ち"),
    (JobStep.FETCH_VIDEO,     "動画取得"),
    (JobStep.FETCH_OAUTH,     "OAuth"),
    (JobStep.UPLOAD_YOUTUBE,  "YT投稿"),
    (JobStep.SAVE_RESULT,     "結果保存"),
]


@method_decorator(login_required, name="dispatch")
class JobHistoryView(View):
    """ログイン中ユーザーの VideoJob 一覧（最新50件）。"""

    def get(self, request):
        jobs = (
            VideoJob.objects
            .filter(user=request.user)
            .order_by("-created_at")[:50]
        )
        return render(request, "jobs/job_history.html", {"jobs": jobs})


@method_decorator(login_required, name="dispatch")
class JobDetailView(View):
    """VideoJob の詳細・進捗・イベントログ。"""

    def get(self, request, job_id: int):
        job = get_object_or_404(VideoJob, id=job_id, user=request.user)
        events = job.events.order_by("created_at")
        return render(request, "jobs/job_detail.html", {
            "job": job,
            "events": events,
            "steps": _STEP_ORDER,
        })
