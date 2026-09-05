from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from notifications.services import send_push_to_user


class Command(BaseCommand):
    help = "Send a Web Push notification to all subscriptions of one Django user."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--title", default="Sunucudan bildirim")
        parser.add_argument("--body", default="Bu bildirim Django management command ile gönderildi.")
        parser.add_argument("--url", default="/")

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist as exc:
            raise CommandError("Kullanıcı bulunamadı.") from exc

        result = send_push_to_user(
            user,
            title=options["title"],
            body=options["body"],
            url=options["url"],
        )
        self.stdout.write(self.style.SUCCESS(f"sent={result['sent']} failed={result['failed']}"))
        if result["errors"]:
            for error in result["errors"]:
                self.stderr.write(error)
