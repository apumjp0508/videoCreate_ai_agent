"""
file_path (CharField) を file (FileField) にリネーム・型変更し、
updated_at フィールドを追加する。
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aivideo_component', '0001_initial'),
    ]

    operations = [
        # ---- GeneratedImage ----
        migrations.RenameField(
            model_name='generatedimage',
            old_name='file_path',
            new_name='file',
        ),
        migrations.AlterField(
            model_name='generatedimage',
            name='file',
            field=models.FileField(upload_to='images/', max_length=500),
        ),
        migrations.AddField(
            model_name='generatedimage',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),

        # ---- GeneratedAudio ----
        migrations.RenameField(
            model_name='generatedaudio',
            old_name='file_path',
            new_name='file',
        ),
        migrations.AlterField(
            model_name='generatedaudio',
            name='file',
            field=models.FileField(upload_to='audios/', max_length=500),
        ),
        migrations.AddField(
            model_name='generatedaudio',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
