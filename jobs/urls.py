"""
jobs アプリの URL 設定。

ページ:
  GET /dashboard/jobs/          ─ 生成履歴一覧
  GET /dashboard/jobs/<id>/     ─ Job 詳細・進捗

API:
  GET /api/jobs/<id>/status/    ─ VideoJob 状態・イベントログ (JSON)
"""
from django.urls import path

from jobs.api import job_status
from jobs.views import JobDetailView, JobHistoryView

app_name = "jobs"

urlpatterns = [
    # ── ページ ──────────────────────────────────────────────────
    path("dashboard/jobs/",          JobHistoryView.as_view(), name="job_history"),
    path("dashboard/jobs/<int:job_id>/", JobDetailView.as_view(),  name="job_detail"),
    # ── REST API ────────────────────────────────────────────────
    path("api/jobs/<int:job_id>/status/", job_status, name="job_status"),
]
