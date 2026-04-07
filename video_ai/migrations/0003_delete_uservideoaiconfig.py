from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('video_ai', '0002_videoaimodel'),
    ]

    operations = [
        migrations.DeleteModel(
            name='UserVideoAiConfig',
        ),
    ]
