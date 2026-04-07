from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0003_prompt_and_videojob_prompt_fk'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='videojob',
            name='video_ai_config_id',
        ),
        migrations.AddField(
            model_name='videojob',
            name='credential_id',
            field=models.IntegerField(
                blank=True,
                null=True,
                help_text='user_video_ai_credentials の id',
            ),
        ),
        migrations.AddField(
            model_name='videojob',
            name='model_id',
            field=models.IntegerField(
                blank=True,
                null=True,
                help_text='video_ai_models の id',
            ),
        ),
    ]
