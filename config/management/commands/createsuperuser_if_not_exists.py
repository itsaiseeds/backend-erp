import os
import logging

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Create superuser if none exists (idempotent, safe for every deploy)"

    def handle(self, *args, **options):
        User = get_user_model()

        if User.objects.filter(is_superuser=True).exists():
            logger.info("Superuser already exists, skipping.")
            return

        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        missing = [
            v for v in ("DJANGO_SUPERUSER_USERNAME", "DJANGO_SUPERUSER_EMAIL", "DJANGO_SUPERUSER_PASSWORD")
            if not os.environ.get(v)
        ]

        if missing:
            msg = f"Missing required env vars: {', '.join(missing)}. Set them in Render dashboard before deploying."
            logger.error(msg)
            raise CommandError(msg)

        User.objects.create_superuser(username=username, email=email, password=password)
        logger.info("Superuser '%s' created.", username)
