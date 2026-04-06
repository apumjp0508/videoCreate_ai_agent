"""
generated_images / generated_audios のカラム構成を更新する。

変更内容:
  - GeneratedImage: channel → youtube_channel (リネーム)
  - GeneratedImage: file    → image_file      (リネーム)
  - GeneratedAudio: channel → youtube_channel (リネーム)
  - GeneratedAudio: file    → audio_file      (リネーム)
  - 両モデルに original_filename / mime_type / file_size_bytes /
    validation_status / validation_message を追加
  - GeneratedImage に width / height / aspect_ratio を追加
  - GeneratedAudio に duration_sec / sample_rate / channels / codec を追加

既存データへの影響:
  - リネームのみで値は保持される
  - 追加カラムはすべて null=True または default='' / default='pending' のため
    既存行への影響はない
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aivideo_component', '0002_alter_file_fields'),
    ]

    operations = [
        # ------------------------------------------------------------------ #
        # GeneratedImage — フィールドリネーム
        # ------------------------------------------------------------------ #
        migrations.RenameField(
            model_name='generatedimage',
            old_name='channel',
            new_name='youtube_channel',
        ),
        migrations.RenameField(
            model_name='generatedimage',
            old_name='file',
            new_name='image_file',
        ),

        # ------------------------------------------------------------------ #
        # GeneratedImage — 新規カラム追加
        # ------------------------------------------------------------------ #
        migrations.AddField(
            model_name='generatedimage',
            name='original_filename',
            field=models.CharField(max_length=500, blank=True, default=''),
        ),
        migrations.AddField(
            model_name='generatedimage',
            name='mime_type',
            field=models.CharField(max_length=100, blank=True, default=''),
        ),
        migrations.AddField(
            model_name='generatedimage',
            name='file_size_bytes',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='generatedimage',
            name='width',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='generatedimage',
            name='height',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='generatedimage',
            name='aspect_ratio',
            field=models.CharField(max_length=20, blank=True, default=''),
        ),
        migrations.AddField(
            model_name='generatedimage',
            name='validation_status',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('pending', '未検証'),
                    ('valid', '適合'),
                    ('invalid', '不適合'),
                    ('warning', '要確認'),
                ],
                default='pending',
            ),
        ),
        migrations.AddField(
            model_name='generatedimage',
            name='validation_message',
            field=models.TextField(blank=True, default=''),
        ),

        # ------------------------------------------------------------------ #
        # GeneratedAudio — フィールドリネーム
        # ------------------------------------------------------------------ #
        migrations.RenameField(
            model_name='generatedaudio',
            old_name='channel',
            new_name='youtube_channel',
        ),
        migrations.RenameField(
            model_name='generatedaudio',
            old_name='file',
            new_name='audio_file',
        ),

        # ------------------------------------------------------------------ #
        # GeneratedAudio — 新規カラム追加
        # ------------------------------------------------------------------ #
        migrations.AddField(
            model_name='generatedaudio',
            name='original_filename',
            field=models.CharField(max_length=500, blank=True, default=''),
        ),
        migrations.AddField(
            model_name='generatedaudio',
            name='mime_type',
            field=models.CharField(max_length=100, blank=True, default=''),
        ),
        migrations.AddField(
            model_name='generatedaudio',
            name='file_size_bytes',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='generatedaudio',
            name='duration_sec',
            field=models.FloatField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='generatedaudio',
            name='sample_rate',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='generatedaudio',
            name='channels',
            field=models.PositiveSmallIntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='generatedaudio',
            name='codec',
            field=models.CharField(max_length=50, blank=True, default=''),
        ),
        migrations.AddField(
            model_name='generatedaudio',
            name='validation_status',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('pending', '未検証'),
                    ('valid', '適合'),
                    ('invalid', '不適合'),
                    ('warning', '要確認'),
                ],
                default='pending',
            ),
        ),
        migrations.AddField(
            model_name='generatedaudio',
            name='validation_message',
            field=models.TextField(blank=True, default=''),
        ),
    ]
