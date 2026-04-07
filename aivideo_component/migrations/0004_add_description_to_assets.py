from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aivideo_component', '0003_update_image_audio_schema'),
    ]

    operations = [
        migrations.AddField(
            model_name='generatedimage',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='generatedaudio',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
    ]
