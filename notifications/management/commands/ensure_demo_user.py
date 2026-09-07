from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the demo user defined in Django settings when missing."

    def handle(self, *args, **options):
        username = settings.DEMO_USERNAME
        password = settings.DEMO_PASSWORD
        email = settings.DEMO_EMAIL
        demo_is_staff = getattr(settings, "DEMO_IS_STAFF", False)
        reset_password = False

        User = get_user_model()
        user, created = User.objects.get_or_create(username=username, defaults={"email": email})

        changed_fields = []
        if created or reset_password:
            user.email = email
            user.set_password(password)
            changed_fields.extend(["email", "password"])

        if user.is_staff != demo_is_staff:
            user.is_staff = demo_is_staff
            changed_fields.append("is_staff")

        if changed_fields:
            user.save(update_fields=list(dict.fromkeys(changed_fields)))

        if created:
            self.stdout.write(self.style.SUCCESS(f"Demo user created: {username}"))
        elif reset_password:
            self.stdout.write(self.style.WARNING(f"Demo user password reset: {username}"))
        else:
            self.stdout.write(f"Demo user already exists: {username}")
        self.stdout.write(f"Demo user staff mode: {demo_is_staff}")
