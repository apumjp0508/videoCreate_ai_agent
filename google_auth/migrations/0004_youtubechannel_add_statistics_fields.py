from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('google_auth', '0003_move_models_to_aivideo_component'),
    ]

    operations = [
        migrations.AddField(
            model_name='youtubechannel',
            name='description',
            field=models.TextField(blank=True, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='youtubechannel',
            name='country',
            field=models.CharField(blank=True, default='', max_length=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='youtubechannel',
            name='uploads_playlist_id',
            field=models.CharField(blank=True, default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='youtubechannel',
            name='subscriber_count',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='youtubechannel',
            name='video_count',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='youtubechannel',
            name='view_count',
            field=models.BigIntegerField(blank=True, null=True),
        ),
    ]
