from django.conf import settings
from django.db import models


class VideoAiProvider(models.Model):
    provider_key = models.CharField(max_length=50, unique=True)
    provider_name = models.CharField(max_length=100)
    api_base_url = models.URLField()
    docs_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'video_ai_providers'

    def __str__(self):
        return self.provider_name


class UserVideoAiCredential(models.Model):
    TEST_STATUS_UNTESTED = 'untested'
    TEST_STATUS_SUCCESS = 'success'
    TEST_STATUS_FAILED = 'failed'
    TEST_STATUS_CHOICES = [
        (TEST_STATUS_UNTESTED, '未テスト'),
        (TEST_STATUS_SUCCESS, '成功'),
        (TEST_STATUS_FAILED, '失敗'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='video_ai_credentials',
    )
    provider = models.ForeignKey(
        VideoAiProvider,
        on_delete=models.CASCADE,
        related_name='credentials',
    )
    api_key = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    test_status = models.CharField(
        max_length=20,
        choices=TEST_STATUS_CHOICES,
        default=TEST_STATUS_UNTESTED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_video_ai_credentials'
        unique_together = ('user', 'provider')

    def __str__(self):
        return f"{self.user.email} - {self.provider.provider_name}"

    def masked_api_key(self):
        if len(self.api_key) <= 8:
            return '****'
        return self.api_key[:4] + '****' + self.api_key[-4:]


class VideoAiModel(models.Model):
    """
    各 AI プロバイダーが提供するモデルの一覧。
    管理画面で登録・有効/無効を操作する。
    ユーザーは Config 作成時にここから選択する。
    """
    provider = models.ForeignKey(
        VideoAiProvider,
        on_delete=models.CASCADE,
        related_name='models',
    )
    model_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'video_ai_models'
        unique_together = ('provider', 'model_name')
        ordering = ['provider', 'model_name']

    def __str__(self):
        return f"{self.provider.provider_name} / {self.model_name}"


