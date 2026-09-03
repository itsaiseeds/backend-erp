import logging
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)

DEV_SUPERUSER_USERNAME = "9999999999"
DEV_SUPERUSER_NAME = "admin"
DEV_SUPERUSER_EMAIL = "admin@example.com"
DEV_SUPERUSER_PASSWORD = "admin"


class Command(BaseCommand):
    help = "Create superuser if none exists (idempotent, safe for every deploy)"

    def handle(self, *args, **options):
        User = get_user_model()

        if User.objects.filter(is_superuser=True).exists():
            logger.info("Superuser already exists, skipping.")
            return

        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        name = os.environ.get("DJANGO_SUPERUSER_NAME")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        missing = [
            v
            for v in (
                "DJANGO_SUPERUSER_USERNAME",
                "DJANGO_SUPERUSER_NAME",
                "DJANGO_SUPERUSER_PASSWORD",
            )
            if not os.environ.get(v)
        ]

        if missing:
            if settings.DEBUG:
                # Local/dev fallback so the app boots without manual env setup.
                username = DEV_SUPERUSER_USERNAME
                name = DEV_SUPERUSER_NAME
                email = DEV_SUPERUSER_EMAIL
                password = DEV_SUPERUSER_PASSWORD
                logger.warning(
                    "Missing %s; using local fallback superuser (%s / %s) because DEBUG=True.",
                    ", ".join(missing),
                    username,
                    password,
                )
            else:
                msg = (
                    f"Missing required env vars: {', '.join(missing)}. "
                    "Set them in the Render dashboard before deploying."
                )
                logger.error(msg)
                raise CommandError(msg)

        # The custom User's USERNAME_FIELD is 'phone_number'.
        User.objects.create_superuser(
            phone_number=username,
            name=name or username,
            email=email,
            password=password,
        )
        logger.info("Superuser '%s' created.", username)
