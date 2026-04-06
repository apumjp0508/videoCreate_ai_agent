from django.conf import settings
from django.db import models


class WorkflowAdminPermission(models.Model):
    """
    Temporal Workflow へのアクセス権限を持つユーザーを管理するテーブル。
    このテーブルに is_active=True で登録されているユーザーのみ
    VideoJobWorkflow を起動できる。
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workflow_admin_permission',
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_workflow_permissions',
    )
    is_active = models.BooleanField(default=True)
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin_workflow'

    def __str__(self):
        status = '有効' if self.is_active else '無効'
        return f"{self.user.email} [{status}]"
