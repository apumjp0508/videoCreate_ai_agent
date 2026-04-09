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
    # ── APIキー検証結果 ──────────────────────────────────────
    validation_http_status = models.IntegerField(
        null=True,
        blank=True,
        help_text='検証リクエストのHTTPステータスコード（未検証時はNULL）',
    )
    validation_endpoint = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text='検証に使用したエンドポイントURL',
    )
    validation_error_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='プロバイダーが返したエラーコード（成功時はNULL）',
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


class VideoAiProviderValidationConfig(models.Model):
    """
    各 AI プロバイダーの入力コンテンツ要件を DB で管理する。
    VideoAiProvider の 1:1 拡張テーブル。

    null=True のカラムは「このプロバイダー固有の制限なし」を意味し、
    共通チェック（common.py）のみが適用される。
    """

    provider = models.OneToOneField(
        VideoAiProvider,
        on_delete=models.CASCADE,
        related_name='validation_config',
        db_column='provider_id',
    )

    # ── 画像: MIME ─────────────────────────────────────────────
    # 例: ["image/jpeg", "image/png", "image/webp"]
    # 共通 MIME を通過したが当プロバイダーで非対応の MIME を弾く
    image_allowed_mime_types = models.JSONField(
        help_text='許可する画像 MIME タイプのリスト',
    )

    # ── 画像: ファイルサイズ ────────────────────────────────────
    image_max_size_bytes = models.BigIntegerField(
        null=True, blank=True,
        help_text='画像ファイルサイズ上限 (bytes)。超過でエラー。null=制限なし',
    )
    image_max_size_soft_bytes = models.BigIntegerField(
        null=True, blank=True,
        help_text='画像ファイルサイズ推奨上限 (bytes)。超過で警告のみ。null=なし',
    )

    # ── 画像: 解像度 (必須 = error) ────────────────────────────
    image_min_dimension = models.IntegerField(
        null=True, blank=True,
        help_text='画像の最小辺長 px (幅・高さ共通)。null=制限なし',
    )
    image_max_dimension = models.IntegerField(
        null=True, blank=True,
        help_text='画像の最大辺長 px (幅・高さ共通)。null=制限なし',
    )

    # ── 画像: 解像度 (推奨 = warning) ─────────────────────────
    image_min_dimension_recommended = models.IntegerField(
        null=True, blank=True,
        help_text='推奨最小辺長 px。下回ると警告。null=なし',
    )
    image_max_dimension_recommended = models.IntegerField(
        null=True, blank=True,
        help_text='推奨最大辺長 px。超えると警告。null=なし',
    )

    # ── 画像: アスペクト比 ─────────────────────────────────────
    # null = アスペクト比制限なし
    # 例: ["16:9", "9:16", "1:1", "4:3", "3:4"]
    image_allowed_aspect_ratios = models.JSONField(
        null=True, blank=True,
        help_text='許可するアスペクト比リスト。null=制限なし',
    )
    # True → リスト外はエラー / False → リスト外は警告のみ
    image_aspect_ratio_required = models.BooleanField(
        default=False,
        help_text='True=アスペクト比制限違反をエラーにする、False=警告のみ',
    )

    # ── 音声: 対応可否 ─────────────────────────────────────────
    audio_is_supported = models.BooleanField(
        default=True,
        help_text='False=このプロバイダーは音声入力に未対応',
    )
    audio_unsupported_message = models.CharField(
        max_length=500, null=True, blank=True,
        help_text='音声未対応時に返すメッセージ',
    )

    # ── 音声: MIME ─────────────────────────────────────────────
    # null = 共通 MIME チェックのみ（プロバイダー固有制限なし）
    audio_allowed_mime_types = models.JSONField(
        null=True, blank=True,
        help_text='許可する音声 MIME タイプリスト。null=共通チェックのみ',
    )

    # ── 音声: ファイルサイズ ────────────────────────────────────
    audio_max_size_bytes = models.BigIntegerField(
        null=True, blank=True,
        help_text='音声ファイルサイズ上限 (bytes)。null=制限なし',
    )

    # ── 音声: 長さ ─────────────────────────────────────────────
    audio_max_duration_sec = models.FloatField(
        null=True, blank=True,
        help_text='音声最大長 (秒)。null=共通チェック (300秒) のみ',
    )

    # ── 音声: サンプルレート ────────────────────────────────────
    audio_min_sample_rate = models.IntegerField(
        null=True, blank=True,
        help_text='最小サンプルレート Hz。null=共通チェックのみ',
    )
    audio_max_sample_rate = models.IntegerField(
        null=True, blank=True,
        help_text='最大サンプルレート Hz。null=共通チェックのみ',
    )

    # ── 音声: チャンネル数 ─────────────────────────────────────
    # 例: [1, 2]
    audio_allowed_channels = models.JSONField(
        null=True, blank=True,
        help_text='許可チャンネル数リスト。null=共通チェックのみ',
    )

    class Meta:
        db_table = 'video_ai_provider_validation_configs'

    def __str__(self):
        return f"{self.provider.provider_name} validation config"


