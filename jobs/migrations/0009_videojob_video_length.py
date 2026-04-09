from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0008_add_generatedvideo_and_videojob_fk'),
    ]

    operations = [
        migrations.AddField(
            model_name='videojob',
            name='video_length',
            field=models.IntegerField(default=5, help_text='動画の長さ（秒）'),
            preserve_default=False,
        ),
    ]
