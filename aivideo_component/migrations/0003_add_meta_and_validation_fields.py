"""
generated_images / generated_audios のカラムを拡張する。

変更内容:
  GeneratedImage:
    - file → image_file (RenameField)
    - original_filename / mime_type / file_size_bytes / width / height /
      aspect_ratio / validation_status / validation_message を追加

  GeneratedAudio:
    - file → audio_file (RenameField)
    - original_filename / mime_type / file_size_bytes / duration_sec /
      sample_rate / channels / codec / validation_status / validation_message を追加

既存レコードへの影響:
  - RenameField はカラム名をリネームするだけで値は保持される。
  - 追加カラムはすべて null=True / blank=True / default 付きのため、
    既存データがあっても安全にマイグレーションできる。
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aivideo_component', '0002_alter_file_fields'),
    ]

    operations = [
        # ────────── GeneratedImage ──────────

        migrations.RenameField(
            model_name='generatedimage',
            old_name='file',
            new_name='image_file',
        ),
        migrations.AddField(
            model_name='generatedimage',
            name='original_filename',
            field=models.CharField(max_length=255, blank=True, default=''),
        ),
        migrations.AddField(
            model_name='generatedimage',
            name='mime_type',
            field=models.CharField(max_length=100, blank=True, default=''),
        ),
        migrations.AddField(
            model_name='generatedimage',
            name='file_size_bytes',
            field=models.BigIntegerField(null=True, blank=True),
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
                ],
                default='pending',
                blank=True,
            ),
        ),
        migrations.AddField(
            model_name='generatedimage',
            name='validation_message',
            field=models.TextField(blank=True, default=''),
        ),

        # ────────── GeneratedAudio ──────────

        migrations.RenameField(
            model_name='generatedaudio',
            old_name='file',
            new_name='audio_file',
        ),
        migrations.AddField(
            model_name='generatedaudio',
            name='original_filename',
            field=models.CharField(max_length=255, blank=True, default=''),
        ),
        migrations.AddField(
            model_name='generatedaudio',
            name='mime_type',
            field=models.CharField(max_length=100, blank=True, default=''),
        ),
        migrations.AddField(
            model_name='generatedaudio',
            name='file_size_bytes',
            field=models.BigIntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='generatedaudio',
            name='duration_sec',
            field=models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True),
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
                ],
                default='pending',
                blank=True,
            ),
        ),
        migrations.AddField(
            model_name='generatedaudio',
            name='validation_message',
            field=models.TextField(blank=True, default=''),
        ),
    ]
