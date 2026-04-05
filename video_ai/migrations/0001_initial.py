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
            name='VideoAiProvider',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider_key', models.CharField(max_length=50, unique=True)),
                ('provider_name', models.CharField(max_length=100)),
                ('api_base_url', models.URLField()),
                ('docs_url', models.URLField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'db_table': 'video_ai_providers',
            },
        ),
        migrations.CreateModel(
            name='UserVideoAiCredential',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('api_key', models.CharField(max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('test_status', models.CharField(
                    choices=[('untested', '未テスト'), ('success', '成功'), ('failed', '失敗')],
                    default='untested',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='video_ai_credentials',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('provider', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='credentials',
                    to='video_ai.videoaiprovider',
                )),
            ],
            options={
                'db_table': 'user_video_ai_credentials',
                'unique_together': {('user', 'provider')},
            },
        ),
        migrations.CreateModel(
            name='UserVideoAiConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('config_name', models.CharField(max_length=100)),
                ('model_name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('is_default', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='video_ai_configs',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('provider', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='configs',
                    to='video_ai.videoaiprovider',
                )),
                ('credential', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='configs',
                    to='video_ai.uservideoaicredential',
                )),
            ],
            options={
                'db_table': 'user_video_ai_configs',
            },
        ),
    ]
