from django.conf import settings
from django.db import models


class UserGoogleAccount(models.Model):
    ACCOUNT_STATUS_ACTIVE = 'active'
    ACCOUNT_STATUS_DISCONNECTED = 'disconnected'
    ACCOUNT_STATUS_ERROR = 'error'
    ACCOUNT_STATUS_CHOICES = [
        (ACCOUNT_STATUS_ACTIVE, 'アクティブ'),
        (ACCOUNT_STATUS_DISCONNECTED, '切断済み'),
        (ACCOUNT_STATUS_ERROR, 'エラー'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='google_accounts',
    )
    # Google側の一意識別子 (JWT の sub クレーム)
    google_sub = models.CharField(max_length=255, unique=True)
    email = models.EmailField()
    name = models.CharField(max_length=255, blank=True)
    picture_url = models.URLField(blank=True)
    account_status = models.CharField(
        max_length=20,
        choices=ACCOUNT_STATUS_CHOICES,
        default=ACCOUNT_STATUS_ACTIVE,
    )
    connected_at = models.DateTimeField(auto_now_add=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'user_google_accounts'

    def __str__(self):
        return f"{self.user.email} - {self.email}"


class OauthToken(models.Model):
    user_google_account = models.OneToOneField(
        UserGoogleAccount,
        on_delete=models.CASCADE,
        related_name='oauth_token',
    )
    # トークンは暗号化して保存する想定 (encrypted suffix で意図を明示)
    access_token_encrypted = models.TextField()
    refresh_token_encrypted = models.TextField(blank=True)
    token_type = models.CharField(max_length=50, default='Bearer')
    scope = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_refreshed_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'oauth_tokens'

    def __str__(self):
        return f"token: {self.user_google_account}"

    @property
    def is_revoked(self):
        return self.revoked_at is not None


class YoutubeChannel(models.Model):
    user_google_account = models.ForeignKey(
        UserGoogleAccount,
        on_delete=models.CASCADE,
        related_name='youtube_channels',
    )
    # YouTube Data API で返される channels.id
    youtube_channel_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255, blank=True)
    # @handle 形式のカスタム URL (snippet.customUrl)
    handle = models.CharField(max_length=255, blank=True)
    thumbnail_url = models.URLField(blank=True)
    # snippet.description
    description = models.TextField(blank=True)
    # snippet.country (例: "JP")
    country = models.CharField(max_length=10, blank=True)
    # contentDetails.relatedPlaylists.uploads
    uploads_playlist_id = models.CharField(max_length=255, blank=True)
    # statistics（YouTube API は文字列で返すが DB には数値で保存）
    subscriber_count = models.BigIntegerField(null=True, blank=True)
    video_count = models.IntegerField(null=True, blank=True)
    view_count = models.BigIntegerField(null=True, blank=True)
    # mine=true で取得したチャンネルのうちデフォルトとして使うもの
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    # channels.list を最後に叩いた日時
    fetched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'youtube_channels'

    def __str__(self):
        return f"{self.title} ({self.youtube_channel_id})"


