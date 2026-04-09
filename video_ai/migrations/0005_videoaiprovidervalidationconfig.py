from django.db import migrations, models
import django.db.models.deletion

_MB = 1024 * 1024

# VideoAiProvider の初期レコード
# 既に存在する場合は get_or_create でスキップする
INITIAL_PROVIDERS = {
    'runway': {
        'provider_name': 'Runway',
        'api_base_url': 'https://api.dev.runwayml.com',
        'docs_url': 'https://docs.dev.runwayml.com',
        'is_active': True,
    },
    'pika': {
        'provider_name': 'Pika',
        'api_base_url': 'https://api.pika.art',
        'docs_url': 'https://pika.art/docs',
        'is_active': True,
    },
    'kling': {
        'provider_name': 'Kling',
        'api_base_url': 'https://api.klingai.com',
        'docs_url': 'https://docs.klingai.com',
        'is_active': True,
    },
}

# provider_key → バリデーション条件のマッピング
INITIAL_CONFIGS = {
    'runway': {
        'image_allowed_mime_types': ['image/jpeg', 'image/png', 'image/webp'],
        'image_max_size_bytes': 16 * _MB,
        'image_max_size_soft_bytes': 5 * _MB,
        'image_min_dimension': None,
        'image_max_dimension': None,
        'image_min_dimension_recommended': 640,
        'image_max_dimension_recommended': 3840,
        'image_allowed_aspect_ratios': None,
        'image_aspect_ratio_required': False,
        'audio_is_supported': True,
        'audio_unsupported_message': None,
        'audio_allowed_mime_types': ['audio/mpeg', 'audio/wav', 'audio/flac', 'audio/mp4', 'audio/aac'],
        'audio_max_size_bytes': 32 * _MB,
        'audio_max_duration_sec': None,
        'audio_min_sample_rate': None,
        'audio_max_sample_rate': None,
        'audio_allowed_channels': None,
    },
    'pika': {
        'image_allowed_mime_types': ['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/avif'],
        'image_max_size_bytes': None,
        'image_max_size_soft_bytes': None,
        'image_min_dimension': 300,
        'image_max_dimension': None,
        'image_min_dimension_recommended': None,
        'image_max_dimension_recommended': None,
        'image_allowed_aspect_ratios': None,
        'image_aspect_ratio_required': False,
        'audio_is_supported': False,
        'audio_unsupported_message': 'Pika: 音声の直接入力は現時点では未対応です（API 仕様確定後に実装予定）',
        'audio_allowed_mime_types': None,
        'audio_max_size_bytes': None,
        'audio_max_duration_sec': None,
        'audio_min_sample_rate': None,
        'audio_max_sample_rate': None,
        'audio_allowed_channels': None,
    },
    'kling': {
        'image_allowed_mime_types': ['image/jpeg', 'image/png'],
        'image_max_size_bytes': 10 * _MB,
        'image_max_size_soft_bytes': None,
        'image_min_dimension': 300,
        'image_max_dimension': None,
        'image_min_dimension_recommended': None,
        'image_max_dimension_recommended': None,
        'image_allowed_aspect_ratios': ['16:9', '9:16', '1:1', '4:3', '3:4'],
        'image_aspect_ratio_required': True,
        'audio_is_supported': False,
        'audio_unsupported_message': 'Kling: 音声の直接入力は現時点では未対応です（API 仕様確定後に実装予定）',
        'audio_allowed_mime_types': None,
        'audio_max_size_bytes': None,
        'audio_max_duration_sec': None,
        'audio_min_sample_rate': None,
        'audio_max_sample_rate': None,
        'audio_allowed_channels': None,
    },
}


def load_initial_configs(apps, schema_editor):
    VideoAiProvider = apps.get_model('video_ai', 'VideoAiProvider')
    VideoAiProviderValidationConfig = apps.get_model('video_ai', 'VideoAiProviderValidationConfig')

    # VideoAiProvider が存在しない場合は作成する
    for provider_key, provider_data in INITIAL_PROVIDERS.items():
        VideoAiProvider.objects.get_or_create(
            provider_key=provider_key,
            defaults=provider_data,
        )

    # validation_config を投入する
    for provider_key, config in INITIAL_CONFIGS.items():
        try:
            provider = VideoAiProvider.objects.get(provider_key=provider_key)
        except VideoAiProvider.DoesNotExist:
            continue
        VideoAiProviderValidationConfig.objects.get_or_create(
            provider=provider,
            defaults=config,
        )


def reverse_load(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('video_ai', '0004_credential_validation_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='VideoAiProviderValidationConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('provider', models.OneToOneField(
                    db_column='provider_id',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='validation_config',
                    to='video_ai.videoaiprovider',
                )),
                ('image_allowed_mime_types', models.JSONField(
                    help_text='許可する画像 MIME タイプのリスト',
                )),
                ('image_max_size_bytes', models.BigIntegerField(
                    blank=True, null=True,
                    help_text='画像ファイルサイズ上限 (bytes)。超過でエラー。null=制限なし',
                )),
                ('image_max_size_soft_bytes', models.BigIntegerField(
                    blank=True, null=True,
                    help_text='画像ファイルサイズ推奨上限 (bytes)。超過で警告のみ。null=なし',
                )),
                ('image_min_dimension', models.IntegerField(
                    blank=True, null=True,
                    help_text='画像の最小辺長 px (幅・高さ共通)。null=制限なし',
                )),
                ('image_max_dimension', models.IntegerField(
                    blank=True, null=True,
                    help_text='画像の最大辺長 px (幅・高さ共通)。null=制限なし',
                )),
                ('image_min_dimension_recommended', models.IntegerField(
                    blank=True, null=True,
                    help_text='推奨最小辺長 px。下回ると警告。null=なし',
                )),
                ('image_max_dimension_recommended', models.IntegerField(
                    blank=True, null=True,
                    help_text='推奨最大辺長 px。超えると警告。null=なし',
                )),
                ('image_allowed_aspect_ratios', models.JSONField(
                    blank=True, null=True,
                    help_text='許可するアスペクト比リスト。null=制限なし',
                )),
                ('image_aspect_ratio_required', models.BooleanField(
                    default=False,
                    help_text='True=アスペクト比制限違反をエラーにする、False=警告のみ',
                )),
                ('audio_is_supported', models.BooleanField(
                    default=True,
                    help_text='False=このプロバイダーは音声入力に未対応',
                )),
                ('audio_unsupported_message', models.CharField(
                    blank=True, max_length=500, null=True,
                    help_text='音声未対応時に返すメッセージ',
                )),
                ('audio_allowed_mime_types', models.JSONField(
                    blank=True, null=True,
                    help_text='許可する音声 MIME タイプリスト。null=共通チェックのみ',
                )),
                ('audio_max_size_bytes', models.BigIntegerField(
                    blank=True, null=True,
                    help_text='音声ファイルサイズ上限 (bytes)。null=制限なし',
                )),
                ('audio_max_duration_sec', models.FloatField(
                    blank=True, null=True,
                    help_text='音声最大長 (秒)。null=共通チェック (300秒) のみ',
                )),
                ('audio_min_sample_rate', models.IntegerField(
                    blank=True, null=True,
                    help_text='最小サンプルレート Hz。null=共通チェックのみ',
                )),
                ('audio_max_sample_rate', models.IntegerField(
                    blank=True, null=True,
                    help_text='最大サンプルレート Hz。null=共通チェックのみ',
                )),
                ('audio_allowed_channels', models.JSONField(
                    blank=True, null=True,
                    help_text='許可チャンネル数リスト。null=共通チェックのみ',
                )),
            ],
            options={'db_table': 'video_ai_provider_validation_configs'},
        ),
        migrations.RunPython(load_initial_configs, reverse_load),
    ]
