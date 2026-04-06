"""
SeparateDatabaseAndState を使って、google_auth で作成済みのテーブルを
aivideo_component の管理下に置く。

テーブル (generated_images, generated_audios) はすでに
google_auth/0002 で作成されているため、SQL は一切実行しない。
state_operations だけで Django の migration 状態を更新する。
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # テーブルが作成された google_auth の migration に依存する
        ('google_auth', '0002_generatedimage_generatedaudio'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='GeneratedImage',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('title', models.CharField(max_length=255)),
                        ('file_path', models.CharField(max_length=500)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('channel', models.ForeignKey(
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name='generated_images',
                            to='google_auth.youtubechannel',
                        )),
                    ],
                    options={
                        'db_table': 'generated_images',
                        'ordering': ['-created_at'],
                    },
                ),
                migrations.CreateModel(
                    name='GeneratedAudio',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('title', models.CharField(max_length=255)),
                        ('file_path', models.CharField(max_length=500)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('channel', models.ForeignKey(
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name='generated_audios',
                            to='google_auth.youtubechannel',
                        )),
                    ],
                    options={
                        'db_table': 'generated_audios',
                        'ordering': ['-created_at'],
                    },
                ),
            ],
            # テーブルは google_auth/0002 で作成済みのため SQL は不要
            database_operations=[],
        ),
    ]
