from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='videojob',
            name='publish_mode',
            field=models.CharField(default='private', max_length=20),
        ),
    ]
