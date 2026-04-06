from django.db import models

from google_auth.models import YoutubeChannel


class GeneratedImage(models.Model):
    """YouTubeチャンネルに紐づく生成済み画像。"""
    channel = models.ForeignKey(
        YoutubeChannel,
        on_delete=models.CASCADE,
        related_name='generated_images',
    )
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='images/', max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'generated_images'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.channel.title})"


class GeneratedAudio(models.Model):
    """YouTubeチャンネルに紐づく生成済み音声。"""
    channel = models.ForeignKey(
        YoutubeChannel,
        on_delete=models.CASCADE,
        related_name='generated_audios',
    )
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='audios/', max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'generated_audios'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.channel.title})"
