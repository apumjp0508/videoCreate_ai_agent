"""
Staging 環境の初期データを一括投入するコマンド。

投入するデータ:
  1. VideoAiProvider / VideoAiModel（seed_ai_models と同内容、冪等）
  2. 管理者ユーザー 1 名（superuser）

管理者の認証情報は以下の優先順位で取得する:
  1. コマンド引数 --email / --password
  2. 環境変数 STAGING_ADMIN_EMAIL / STAGING_ADMIN_PASSWORD
  3. デフォルト値（admin@example.com / 変更必須）

実行:
    python manage.py seed_staging
    python manage.py seed_staging --email admin@myapp.com --password MySecurePass1!

冪等: 既存レコードはスキップする（重複しない）。
"""
import os

from django.core.management import call_command
from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    help = "Staging 環境の初期データを投入する（AI providers/models + 管理者ユーザー）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            default=None,
            help="管理者ユーザーのメールアドレス（省略時は環境変数 STAGING_ADMIN_EMAIL）",
        )
        parser.add_argument(
            "--password",
            default=None,
            help="管理者ユーザーのパスワード（省略時は環境変数 STAGING_ADMIN_PASSWORD）",
        )

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("🚀 seed_staging start")
        self.stdout.write("=" * 60)

        # ── 1. AI プロバイダー / モデル ───────────────────────────────
        self.stdout.write("\n[1/2] VideoAiProvider / VideoAiModel を投入中...")
        call_command("seed_ai_models", stdout=self.stdout, stderr=self.stderr)

        # ── 2. 管理者ユーザー ─────────────────────────────────────────
        self.stdout.write("\n[2/2] 管理者ユーザーを作成中...")

        email = (
            options["email"]
            or os.environ.get("STAGING_ADMIN_EMAIL", "admin@example.com")
        )
        password = (
            options["password"]
            or os.environ.get("STAGING_ADMIN_PASSWORD")
        )

        if not password:
            self.stderr.write(
                self.style.ERROR(
                    "パスワードが未設定です。"
                    "--password オプションまたは環境変数 STAGING_ADMIN_PASSWORD を設定してください。"
                )
            )
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(f"  skip: {email} (already exists)")
        else:
            User.objects.create_superuser(email=email, password=password)
            self.stdout.write(
                self.style.SUCCESS(f"  created superuser: {email}")
            )

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("✅ seed_staging complete"))
        self.stdout.write("=" * 60)
