from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from .fields import EncryptedTextField


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # カラムはここに追加していく

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.email


class OAuthAccount(models.Model):
    PROVIDER_YOUTUBE = 'youtube'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='oauth_accounts')
    provider = models.CharField(max_length=50)
    access_token = EncryptedTextField()
    refresh_token = EncryptedTextField()
    token_expiry = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'oauth_accounts'
        unique_together = ('user', 'provider')

    def __str__(self):
        return f'{self.user.email} - {self.provider}'


class YouTubeChannel(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='youtube_channel')
    oauth_account = models.OneToOneField(OAuthAccount, on_delete=models.CASCADE, related_name='youtube_channel')
    channel_id = models.CharField(max_length=255)
    channel_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'youtube_channels'

    def __str__(self):
        return f'{self.user.email} - {self.channel_name}'


class Project(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_PAUSED = 'paused'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_PAUSED, 'Paused'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    target_platform = models.CharField(max_length=50, blank=True)
    target_language = models.CharField(max_length=20, blank=True)
    target_region = models.CharField(max_length=20, blank=True)
    genre = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'projects'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} - {self.name}'
