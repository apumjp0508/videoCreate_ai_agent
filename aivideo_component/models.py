from django.db import models

from google_auth.models import YoutubeChannel


class GeneratedImage(models.Model):
    """YouTubeチャンネルに紐づく画像ファイル。将来の動画AI適合判定に使うメタ情報を保持する。"""

    VALIDATION_PENDING = 'pending'
    VALIDATION_VALID = 'valid'
    VALIDATION_INVALID = 'invalid'
    VALIDATION_WARNING = 'warning'
    VALIDATION_STATUS_CHOICES = [
        (VALIDATION_PENDING, '未検証'),
        (VALIDATION_VALID, '適合'),
        (VALIDATION_INVALID, '不適合'),
        (VALIDATION_WARNING, '要確認'),
    ]

    youtube_channel = models.ForeignKey(
        YoutubeChannel,
        on_delete=models.CASCADE,
        related_name='generated_images',
    )
    title = models.CharField(max_length=255)
    image_file = models.FileField(upload_to='images/', max_length=500)

    # --- ファイルメタ情報 (アップロード後に抽出・保存予定) ---
    original_filename = models.CharField(max_length=500, blank=True, default='')
    mime_type = models.CharField(max_length=100, blank=True, default='')
    file_size_bytes = models.PositiveIntegerField(null=True, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    # 例: "16:9", "1:1", "9:16" — width/height から算出して保存予定
    aspect_ratio = models.CharField(max_length=20, blank=True, default='')

    # --- 動画AI適合判定 (将来の判定ロジックで書き込み予定) ---
    validation_status = models.CharField(
        max_length=20,
        choices=VALIDATION_STATUS_CHOICES,
        default=VALIDATION_PENDING,
    )
    # 例: "Runwayでは使用可能 / Klingではアスペクト比が推奨外"
    validation_message = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'generated_images'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.youtube_channel.title})"


class GeneratedAudio(models.Model):
    """YouTubeチャンネルに紐づく音声ファイル。将来の動画AI適合判定に使うメタ情報を保持する。"""

    VALIDATION_PENDING = 'pending'
    VALIDATION_VALID = 'valid'
    VALIDATION_INVALID = 'invalid'
    VALIDATION_WARNING = 'warning'
    VALIDATION_STATUS_CHOICES = [
        (VALIDATION_PENDING, '未検証'),
        (VALIDATION_VALID, '適合'),
        (VALIDATION_INVALID, '不適合'),
        (VALIDATION_WARNING, '要確認'),
    ]

    youtube_channel = models.ForeignKey(
        YoutubeChannel,
        on_delete=models.CASCADE,
        related_name='generated_audios',
    )
    title = models.CharField(max_length=255)
    audio_file = models.FileField(upload_to='audios/', max_length=500)

    # --- ファイルメタ情報 (アップロード後に抽出・保存予定) ---
    original_filename = models.CharField(max_length=500, blank=True, default='')
    mime_type = models.CharField(max_length=100, blank=True, default='')
    file_size_bytes = models.PositiveIntegerField(null=True, blank=True)
    # 秒単位 (例: 30.5)
    duration_sec = models.FloatField(null=True, blank=True)
    # Hz単位 (例: 44100)
    sample_rate = models.PositiveIntegerField(null=True, blank=True)
    # 1=モノラル, 2=ステレオ
    channels = models.PositiveSmallIntegerField(null=True, blank=True)
    # 例: "mp3", "aac", "wav"
    codec = models.CharField(max_length=50, blank=True, default='')

    # --- 動画AI適合判定 (将来の判定ロジックで書き込み予定) ---
    validation_status = models.CharField(
        max_length=20,
        choices=VALIDATION_STATUS_CHOICES,
        default=VALIDATION_PENDING,
    )
    # 例: "音声の長さが長すぎる / Pikaは要確認"
    validation_message = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'generated_audios'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.youtube_channel.title})"
