
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the demo user defined in Django settings when missing."

    def handle(self, *args, **options):
        username = settings.DEMO_USERNAME
        password = settings.DEMO_PASSWORD
        email = settings.DEMO_EMAIL
        reset_password = False

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
