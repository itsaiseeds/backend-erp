from django.apps import AppConfig
from django.core.checks import register


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "common"
    verbose_name = "Common (reusable abstract base models)"

    def ready(self):
        from .checks import images_have_durable_storage

        register(images_have_durable_storage)
