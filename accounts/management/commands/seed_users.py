from django.core.management.base import BaseCommand
from accounts.models import User


MOCK_USERS = [
    {
        "email": "alice@example.com",
        "password": "password123",
        "is_staff": False,
    },
    {
        "email": "bob@example.com",
        "password": "password123",
        "is_staff": True,
    },
]


class Command(BaseCommand):
    help = "Insert mock users for development"

    def handle(self, *args, **kwargs):
        for data in MOCK_USERS:
            email = data["email"]
            if User.objects.filter(email=email).exists():
                self.stdout.write(f"  skip: {email} (already exists)")
                continue
            User.objects.create_user(
                email=email,
                password=data["password"],
                is_staff=data.get("is_staff", False),
            )
            self.stdout.write(self.style.SUCCESS(f"  created: {email}"))

        self.stdout.write(self.style.SUCCESS("✅ seed_users complete"))
