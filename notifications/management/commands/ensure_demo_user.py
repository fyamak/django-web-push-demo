import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a demo user from environment variables when missing."

    def handle(self, *args, **options):
        username = os.getenv("DEMO_USERNAME", "demo")
        password = os.getenv("DEMO_PASSWORD", "Demo12345!")
        email = os.getenv("DEMO_EMAIL", "demo@example.com")
        reset_password = os.getenv("RESET_DEMO_PASSWORD", "0") == "1"

        User = get_user_model()
        user, created = User.objects.get_or_create(username=username, defaults={"email": email})

        if created or reset_password:
            user.email = email
            user.set_password(password)
            user.save(update_fields=["email", "password"])

        if created:
            self.stdout.write(self.style.SUCCESS(f"Demo user created: {username}"))
        elif reset_password:
            self.stdout.write(self.style.WARNING(f"Demo user password reset: {username}"))
        else:
            self.stdout.write(f"Demo user already exists: {username}")
