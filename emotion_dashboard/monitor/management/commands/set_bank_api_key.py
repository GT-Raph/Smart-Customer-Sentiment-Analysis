import secrets

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from monitor.models import Bank


class Command(BaseCommand):
    help = (
        "Create or replace a bank upload API key. "
        "The raw key is printed only once."
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "bank_code"
        )

        parser.add_argument(
            "--key",
            dest="raw_key",
        )

    def handle(
        self,
        *args,
        **options,
    ):
        bank_code = (
            options["bank_code"]
            .strip()
            .upper()
        )

        try:
            bank = Bank.objects.get(
                code=bank_code
            )

        except Bank.DoesNotExist as error:
            raise CommandError(
                (
                    f"Bank {bank_code!r} "
                    f"does not exist."
                )
            ) from error

        raw_key = (
            options.get("raw_key")
            or secrets.token_urlsafe(32)
        )

        bank.set_api_key(
            raw_key
        )

        bank.save(
            update_fields=[
                "api_key_hash",
                "api_key_rotated_at",
            ]
        )

        self.stdout.write(
            self.style.SUCCESS(
                (
                    f"API key updated for "
                    f"{bank.code}."
                )
            )
        )

        self.stdout.write(
            (
                "Copy this key now. "
                "It is not stored in plain text:"
            )
        )

        self.stdout.write(
            raw_key
        )