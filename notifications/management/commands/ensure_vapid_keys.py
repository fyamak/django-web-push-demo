import base64
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a persistent VAPID P-256 key pair if it does not exist."

    def handle(self, *args, **options):
        private_path = Path(settings.VAPID_PRIVATE_KEY_PATH)
        public_path = Path(settings.VAPID_PUBLIC_KEY_PATH)
        private_path.parent.mkdir(parents=True, exist_ok=True)
        public_path.parent.mkdir(parents=True, exist_ok=True)

        if private_path.exists() and public_path.exists():
            self.stdout.write(self.style.SUCCESS("VAPID keys already exist."))
            return

        private_key = ec.generate_private_key(ec.SECP256R1())
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

        numbers = private_key.public_key().public_numbers()
        raw_public_key = (
            b"\x04"
            + numbers.x.to_bytes(32, "big")
            + numbers.y.to_bytes(32, "big")
        )
        public_key_b64 = base64.urlsafe_b64encode(raw_public_key).rstrip(b"=").decode("ascii")

        private_path.write_bytes(private_pem)
        public_path.write_text(public_key_b64 + "\n", encoding="utf-8")
        private_path.chmod(0o600)

        self.stdout.write(self.style.SUCCESS(f"VAPID key pair created in {private_path.parent}"))
