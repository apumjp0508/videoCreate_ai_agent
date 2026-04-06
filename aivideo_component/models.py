from django.db import models

from google_auth.models import YoutubeChannel


class GeneratedImage(models.Model):
    """YouTubeチャンネルに紐づく生成済み画像。"""

    # バリデーション状態の選択肢（将来のprovider適合判定で書き込む）
    VALIDATION_PENDING = 'pending'
    VALIDATION_VALID = 'valid'
    VALIDATION_INVALID = 'invalid'
    VALIDATION_STATUS_CHOICES = [
        (VALIDATION_PENDING, '未検証'),
        (VALIDATION_VALID, '適合'),
        (VALIDATION_INVALID, '不適合'),
    ]

    channel = models.ForeignKey(
        YoutubeChannel,
        on_delete=models.CASCADE,
        related_name='generated_images',
    )
    title = models.CharField(max_length=255)
    image_file = models.FileField(upload_to='images/', max_length=500)

    # ファイルメタ情報（将来のメタ情報抽出処理で書き込む）
    original_filename = models.CharField(max_length=255, blank=True, default='')
    mime_type = models.CharField(max_length=100, blank=True, default='')
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    # "16:9" / "1:1" / "9:16" 形式で保持
    aspect_ratio = models.CharField(max_length=20, blank=True, default='')

    # バリデーション（将来のprovider適合判定処理で書き込む）
    validation_status = models.CharField(
        max_length=20,
        choices=VALIDATION_STATUS_CHOICES,
        default=VALIDATION_PENDING,
        blank=True,
    )
    # provider ごとのメッセージを改行区切りなどで自由に格納できる
    validation_message = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'generated_images'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.channel.title})"


class GeneratedAudio(models.Model):
    """YouTubeチャンネルに紐づく生成済み音声。"""

    # バリデーション状態の選択肢（将来のprovider適合判定で書き込む）
    VALIDATION_PENDING = 'pending'
    VALIDATION_VALID = 'valid'
    VALIDATION_INVALID = 'invalid'
    VALIDATION_STATUS_CHOICES = [
        (VALIDATION_PENDING, '未検証'),
        (VALIDATION_VALID, '適合'),
        (VALIDATION_INVALID, '不適合'),
    ]

    channel = models.ForeignKey(
        YoutubeChannel,
        on_delete=models.CASCADE,
        related_name='generated_audios',
    )
    title = models.CharField(max_length=255)
    audio_file = models.FileField(upload_to='audios/', max_length=500)

    # ファイルメタ情報（将来のメタ情報抽出処理で書き込む）
    original_filename = models.CharField(max_length=255, blank=True, default='')
    mime_type = models.CharField(max_length=100, blank=True, default='')
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    # 秒単位・小数点3桁まで（例: 125.340）
    duration_sec = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    sample_rate = models.PositiveIntegerField(null=True, blank=True)
    channels = models.PositiveSmallIntegerField(null=True, blank=True)
    codec = models.CharField(max_length=50, blank=True, default='')

    # バリデーション（将来のprovider適合判定処理で書き込む）
    validation_status = models.CharField(
        max_length=20,
        choices=VALIDATION_STATUS_CHOICES,
        default=VALIDATION_PENDING,
        blank=True,
    )
    # provider ごとのメッセージを改行区切りなどで自由に格納できる
    validation_message = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'generated_audios'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.channel.title})"
