import hashlib
import secrets

from django.core.management.base import BaseCommand, CommandError

from monitor.models import Branch, Device


class Command(BaseCommand):
    help = "Create a device and print its API key once"

    def add_arguments(self, parser):
        parser.add_argument("--branch", required=True, type=int, help="Branch ID")
        parser.add_argument("--name", required=True)
        parser.add_argument("--pc-name", required=True)

    def handle(self, *args, **options):
        try:
            branch = Branch.objects.get(id=options["branch"], is_active=True)
        except Branch.DoesNotExist as exc:
            raise CommandError("Active branch not found") from exc

        if Device.objects.filter(pc_name=options["pc_name"]).exists():
            raise CommandError("A device with that PC name already exists")

        prefix = secrets.token_hex(6)
        token = f"scs_{prefix}_{secrets.token_urlsafe(32)}"
        Device.objects.create(
            branch=branch,
            name=options["name"],
            pc_name=options["pc_name"],
            api_key_prefix=prefix,
            api_key_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        )
        self.stdout.write(self.style.SUCCESS("Device created. Store this key now; it will not be shown again:"))
        self.stdout.write(token)
