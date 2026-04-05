from django.core.management.base import BaseCommand

from video_ai.models import VideoAiProvider

PROVIDERS = [
    {
        'provider_key': 'runway',
        'provider_name': 'Runway',
        'api_base_url': 'https://api.runwayml.com',
        'docs_url': 'https://docs.runwayml.com',
        'is_active': True,
    },
    {
        'provider_key': 'pika',
        'provider_name': 'Pika',
        'api_base_url': 'https://api.pika.art',
        'docs_url': 'https://docs.pika.art',
        'is_active': True,
    },
    {
        'provider_key': 'kling',
        'provider_name': 'Kling',
        'api_base_url': 'https://api.klingai.com',
        'docs_url': 'https://docs.klingai.com',
        'is_active': True,
    },
]


class Command(BaseCommand):
    help = '動画生成AIプロバイダーの初期データを登録します'

    def handle(self, *args, **options):
        for data in PROVIDERS:
            provider, created = VideoAiProvider.objects.update_or_create(
                provider_key=data['provider_key'],
                defaults=data,
            )
            status = '作成' if created else '更新'
            self.stdout.write(self.style.SUCCESS(f'[{status}] {provider.provider_name}'))

        self.stdout.write(self.style.SUCCESS('プロバイダーデータの登録が完了しました'))
