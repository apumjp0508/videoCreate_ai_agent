from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('google_auth', '0001_initial'),
    ]

    operations = [
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
    ]
