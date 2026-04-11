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
        "api_base_url": "https://api.runwayml.com/v1",
        "docs_url": "https://docs.runwayml.com/",
        "is_active": True,
        "models": [
            {"model_name": "gen3a_turbo", "is_active": True},
            {"model_name": "gen3a",       "is_active": True},
        ],
    },
    {
        "provider_key": "kling",
        "provider_name": "Kling AI",
        "api_base_url": "https://api.klingai.com/v1",
        "docs_url": "https://docs.klingai.com/",
        "is_active": True,
        "models": [
            {"model_name": "kling-v1",      "is_active": True},
            {"model_name": "kling-v1-5",    "is_active": True},
            {"model_name": "kling-v2-master", "is_active": True},
        ],
    },
    {
        "provider_key": "pika",
        "provider_name": "Pika",
        "api_base_url": "https://api.pika.art/v1",
        "docs_url": "https://pika.art/",
        "is_active": True,
        "models": [
            {"model_name": "pika-2.2",   "is_active": True},
            {"model_name": "pika-2.1",   "is_active": False},
        ],
    },
    {
        "provider_key": "luma",
        "provider_name": "Luma AI (Dream Machine)",
        "api_base_url": "https://api.lumalabs.ai/dream-machine/v1",
        "docs_url": "https://lumalabs.ai/dream-machine/api",
        "is_active": True,
        "models": [
            {"model_name": "dream-machine", "is_active": True},
            {"model_name": "ray2-flash",    "is_active": True},
        ],
    },
    {
        "provider_key": "replicate",
        "provider_name": "Replicate",
        "api_base_url": "https://api.replicate.com/v1",
        "docs_url": "https://replicate.com/docs",
        "is_active": True,
        "models": [
            # テキスト + 画像 → 動画生成
            {"model_name": "minimax/video-01",        "is_active": True},
            # 動画アップスケール（4K化・FPS補完）
            {"model_name": "topazlabs/video-upscale", "is_active": True},
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

            provider, created = VideoAiProvider.objects.get_or_create(
                provider_key=pdata["provider_key"],
                defaults=pdata,
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"  [Provider] created: {provider.provider_name}")
                )
                total_providers += 1
            else:
                self.stdout.write(f"  [Provider] skip:    {provider.provider_name}")

            for mdata in models_data:
                model, m_created = VideoAiModel.objects.get_or_create(
                    provider=provider,
                    model_name=mdata["model_name"],
                    defaults={"is_active": mdata["is_active"]},
                )
                if m_created:
                    status = "✓" if model.is_active else "✗"
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"    [Model] created: {provider.provider_key} / {model.model_name} [{status}]"
                        )
                    )
                    total_models += 1
                else:
                    self.stdout.write(
                        f"    [Model] skip:    {provider.provider_key} / {model.model_name}"
                    )

        self.stdout.write("─" * 50)
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ seed_ai_models complete  providers={total_providers}  models={total_models}"
            )
        )
