from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserGoogleAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('google_sub', models.CharField(max_length=255, unique=True)),
                ('email', models.EmailField(max_length=254)),
                ('name', models.CharField(blank=True, max_length=255)),
                ('picture_url', models.URLField(blank=True)),
                ('account_status', models.CharField(
                    choices=[('active', 'アクティブ'), ('disconnected', '切断済み'), ('error', 'エラー')],
                    default='active',
                    max_length=20,
                )),
                ('connected_at', models.DateTimeField(auto_now_add=True)),
                ('disconnected_at', models.DateTimeField(blank=True, null=True)),
                ('last_synced_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='google_accounts',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'user_google_accounts',
            },
        ),
        migrations.CreateModel(
            name='OauthToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('access_token_encrypted', models.TextField()),
                ('refresh_token_encrypted', models.TextField(blank=True)),
                ('token_type', models.CharField(default='Bearer', max_length=50)),
                ('scope', models.TextField(blank=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('last_refreshed_at', models.DateTimeField(blank=True, null=True)),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                ('user_google_account', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='oauth_token',
                    to='google_auth.usergoogleaccount',
                )),
            ],
            options={
                'db_table': 'oauth_tokens',
            },
        ),
        migrations.CreateModel(
            name='YoutubeChannel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('youtube_channel_id', models.CharField(max_length=255, unique=True)),
                ('title', models.CharField(blank=True, max_length=255)),
                ('handle', models.CharField(blank=True, max_length=255)),
                ('thumbnail_url', models.URLField(blank=True)),
                ('is_default', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('fetched_at', models.DateTimeField(blank=True, null=True)),
                ('user_google_account', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='youtube_channels',
                    to='google_auth.usergoogleaccount',
                )),
            ],
            options={
                'db_table': 'youtube_channels',
            },
        ),
    ]
