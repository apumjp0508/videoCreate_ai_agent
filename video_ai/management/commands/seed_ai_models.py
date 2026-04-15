"""
AI プロバイダーとモデルのシーダー。

実行:
    python manage.py seed_ai_models

冪等: 既存レコードはスキップする（重複しない）。
"""
from django.core.management.base import BaseCommand

from video_ai.models import VideoAiModel, VideoAiProvider


# ─────────────────────────────────────────────────────────────
# シードデータ定義
# ─────────────────────────────────────────────────────────────

PROVIDERS = [
    {
        "provider_key": "runway",
        "provider_name": "Runway",
        "api_base_url": "https://api.dev.runwayml.com/v1",
        "docs_url": "https://docs.runwayml.com/",
        "is_active": True,
        "models": [
            {"model_name": "gen4_turbo", "is_active": True},
        ],
    },
    {
        "provider_key": "kling",
        "provider_name": "Kling AI",
        "api_base_url": "https://api.klingai.com/v1",
        "docs_url": "https://docs.klingai.com/",
        "is_active": False,
        "models": [
            {"model_name": "kling-v1",        "is_active": False},
            {"model_name": "kling-v1-5",      "is_active": False},
            {"model_name": "kling-v2-master",  "is_active": False},
        ],
    },
    {
        "provider_key": "pika",
        "provider_name": "Pika",
        "api_base_url": "https://api.pika.art/v1",
        "docs_url": "https://pika.art/",
        "is_active": False,
        "models": [
            {"model_name": "pika-2.2", "is_active": False},
            {"model_name": "pika-2.1", "is_active": False},
        ],
    },
    {
        "provider_key": "luma",
        "provider_name": "Luma AI (Dream Machine)",
        "api_base_url": "https://api.lumalabs.ai/dream-machine/v1",
        "docs_url": "https://lumalabs.ai/dream-machine/api",
        "is_active": False,
        "models": [
            {"model_name": "dream-machine", "is_active": False},
            {"model_name": "ray2-flash",    "is_active": False},
        ],
    },
    {
        "provider_key": "replicate",
        "provider_name": "Replicate",
        "api_base_url": "https://api.replicate.com/v1",
        "docs_url": "https://replicate.com/docs",
        "is_active": False,
        "models": [
            {"model_name": "minimax/video-01",        "is_active": False},
            {"model_name": "topazlabs/video-upscale", "is_active": False},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed VideoAiProvider and VideoAiModel records for development"

    def handle(self, *args, **kwargs):
        self.stdout.write("─" * 50)
        self.stdout.write("🌱 seed_ai_models start")
        self.stdout.write("─" * 50)

        total_providers = 0
        total_models = 0

        for pdata in PROVIDERS:
            models_data = pdata.pop("models")

            provider, created = VideoAiProvider.objects.update_or_create(
                provider_key=pdata["provider_key"],
                defaults=pdata,
            )
            action = "created" if created else "updated"
            self.stdout.write(
                self.style.SUCCESS(f"  [Provider] {action}: {provider.provider_name}")
            )
            if created:
                total_providers += 1

            for mdata in models_data:
                model, m_created = VideoAiModel.objects.update_or_create(
                    provider=provider,
                    model_name=mdata["model_name"],
                    defaults={"is_active": mdata["is_active"]},
                )
                m_action = "created" if m_created else "updated"
                status = "✓" if model.is_active else "✗"
                self.stdout.write(
                    self.style.SUCCESS(
                        f"    [Model] {m_action}: {provider.provider_key} / {model.model_name} [{status}]"
                    )
                )
                if m_created:
                    total_models += 1

        self.stdout.write("─" * 50)
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ seed_ai_models complete  providers={total_providers}  models={total_models}"
            )
        )
