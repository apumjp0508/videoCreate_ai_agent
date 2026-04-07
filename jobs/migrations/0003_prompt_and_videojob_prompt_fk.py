import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0002_videojob_publish_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. prompts テーブル作成
        migrations.CreateModel(
            name='Prompt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prompt_text', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='prompts',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'prompts',
            },
        ),
        # 2. video_jobs に prompt FK 追加
        migrations.AddField(
            model_name='videojob',
            name='prompt',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='video_jobs',
                to='jobs.prompt',
            ),
        ),
        # 3. video_jobs から prompt_text カラム削除
        migrations.RemoveField(
            model_name='videojob',
            name='prompt_text',
        ),
    ]
