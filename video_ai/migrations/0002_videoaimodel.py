from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('video_ai', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='VideoAiModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model_name', models.CharField(max_length=100)),
                ('is_active', models.BooleanField(default=True)),
                ('provider', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='models',
                    to='video_ai.videoaiprovider',
                )),
            ],
            options={
                'db_table': 'video_ai_models',
                'ordering': ['provider', 'model_name'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='videoaimodel',
            unique_together={('provider', 'model_name')},
        ),
    ]
