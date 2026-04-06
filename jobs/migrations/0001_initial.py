import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('google_auth', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='VideoJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[
                        ('queued',     '待機中'),
                        ('generating', '動画生成中'),
                        ('generated',  '動画生成完了'),
                        ('publishing', 'YouTube投稿中'),
                        ('completed',  '完了'),
                        ('failed',     '失敗'),
                        ('cancelled',  'キャンセル'),
                    ],
                    db_index=True,
                    default='queued',
                    max_length=20,
                )),
                ('request_type', models.CharField(
                    choices=[
                        ('generate_only',        '動画生成のみ'),
                        ('generate_and_publish', '動画生成 + YouTube投稿'),
                    ],
                    default='generate_and_publish',
                    max_length=30,
                )),
                ('prompt_text', models.TextField(blank=True)),
                ('video_ai_config_id', models.IntegerField(
                    blank=True,
                    help_text='video_ai.UserVideoAiConfig の id',
                    null=True,
                )),
                ('temporal_workflow_id', models.CharField(blank=True, db_index=True, max_length=255)),
                ('temporal_run_id',      models.CharField(blank=True, max_length=255)),
                ('current_step', models.CharField(
                    blank=True,
                    choices=[
                        ('FETCH_ASSETS',    '素材取得'),
                        ('FETCH_AI_CONFIG', 'AI設定取得'),
                        ('CALL_AI',         'AI呼び出し'),
                        ('WAIT_AI_RESULT',  'AI生成待ち'),
                        ('FETCH_VIDEO',     '完成動画取得'),
                        ('FETCH_OAUTH',     'OAuthトークン取得'),
                        ('UPLOAD_YOUTUBE',  'YouTubeアップロード'),
                        ('SAVE_RESULT',     '結果保存'),
                    ],
                    max_length=30,
                )),
                ('error_code',    models.CharField(blank=True, max_length=64)),
                ('error_message', models.TextField(blank=True)),
                ('created_at',   models.DateTimeField(auto_now_add=True)),
                ('updated_at',   models.DateTimeField(auto_now=True)),
                ('started_at',   models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='video_jobs',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('google_account', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='video_jobs',
                    to='google_auth.usergoogleaccount',
                )),
                ('youtube_channel', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='video_jobs',
                    to='google_auth.youtubechannel',
                )),
            ],
            options={
                'db_table': 'video_jobs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='VideoJobAsset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('asset_id', models.IntegerField(help_text='各素材テーブルの PK')),
                ('asset_role', models.CharField(
                    choices=[
                        ('main_image',       'メイン画像'),
                        ('bgm',              'BGM'),
                        ('narration',        'ナレーション'),
                        ('subtitle',         '字幕'),
                        ('thumbnail_source', 'サムネイル素材'),
                    ],
                    max_length=30,
                )),
                ('job', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='assets',
                    to='jobs.videojob',
                )),
            ],
            options={
                'db_table': 'video_job_assets',
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='VideoJobEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(
                    choices=[
                        ('JOB_CREATED',              'Job作成'),
                        ('WORKFLOW_STARTED',          'Workflow開始'),
                        ('AI_REQUEST_SENT',           'AIリクエスト送信'),
                        ('AI_RENDER_COMPLETED',       'AI生成完了'),
                        ('YOUTUBE_UPLOAD_STARTED',    'YouTubeアップロード開始'),
                        ('YOUTUBE_UPLOAD_COMPLETED',  'YouTubeアップロード完了'),
                        ('JOB_COMPLETED',             'Job完了'),
                        ('JOB_FAILED',                'Job失敗'),
                        ('JOB_CANCELLED',             'Jobキャンセル'),
                    ],
                    db_index=True,
                    max_length=40,
                )),
                ('step_name',    models.CharField(blank=True, max_length=30)),
                ('message',      models.TextField(blank=True)),
                ('payload_json', models.JSONField(blank=True, null=True)),
                ('created_at',   models.DateTimeField(auto_now_add=True)),
                ('job', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='events',
                    to='jobs.videojob',
                )),
            ],
            options={
                'db_table': 'video_job_events',
                'ordering': ['created_at'],
            },
        ),
    ]
