from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0005_videojob_youtube_result_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='VideoJobAsset',
            name='description',
            field=models.TextField(default='', help_text='このJobでの素材の用途説明'),
            preserve_default=False,
        ),
    ]
