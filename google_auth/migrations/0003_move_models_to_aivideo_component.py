"""
SeparateDatabaseAndState を使って GeneratedImage / GeneratedAudio の
ownership を google_auth から aivideo_component へ移す。

テーブルそのものはそのまま残すため database_operations は空。
state_operations だけで Django の migration 状態から削除する。
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('google_auth', '0002_generatedimage_generatedaudio'),
        # aivideo_component 側でモデルの state が登録された後に実行する
        ('aivideo_component', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='GeneratedImage'),
                migrations.DeleteModel(name='GeneratedAudio'),
            ],
            # テーブルは aivideo_component 管理として残すため DROP しない
            database_operations=[],
        ),
    ]
