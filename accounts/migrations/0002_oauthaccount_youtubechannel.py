from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import accounts.fields


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='OAuthAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(max_length=50)),
                ('access_token', accounts.fields.EncryptedTextField()),
                ('refresh_token', accounts.fields.EncryptedTextField()),
                ('token_expiry', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='oauth_accounts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'oauth_accounts',
                'unique_together': {('user', 'provider')},
            },
        ),
        migrations.CreateModel(
            name='YouTubeChannel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('channel_id', models.CharField(max_length=255)),
                ('channel_name', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='youtube_channel', to=settings.AUTH_USER_MODEL)),
                ('oauth_account', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='youtube_channel', to='accounts.oauthaccount')),
            ],
            options={
                'db_table': 'youtube_channels',
            },
        ),
    ]
