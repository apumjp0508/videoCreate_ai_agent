from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('video_ai', '0003_delete_uservideoaiconfig'),
    ]

    operations = [
        migrations.AddField(
            model_name='uservideoaicredential',
            name='validation_http_status',
            field=models.IntegerField(
                blank=True,
                null=True,
                help_text='検証リクエストのHTTPステータスコード（未検証時はNULL）',
            ),
        ),
        migrations.AddField(
            model_name='uservideoaicredential',
            name='validation_endpoint',
            field=models.CharField(
                blank=True,
                max_length=500,
                null=True,
                help_text='検証に使用したエンドポイントURL',
            ),
        ),
        migrations.AddField(
            model_name='uservideoaicredential',
            name='validation_error_code',
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                help_text='プロバイダーが返したエラーコード（成功時はNULL）',
            ),
        ),
    ]
