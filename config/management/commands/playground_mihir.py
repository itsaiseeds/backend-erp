import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Playground command for experimenting with ORM queries and app logic."

    def handle(self, *args, **options):
        logging.info("playground_mihir: start")

        # Add experimental code here.

        User = get_user_model()
        user = User.objects.get(id=3)
        logging.info(f"User with ID 3: {user.name}, Role: {user.role}")

        logging.info("playground_mihir: done")
