from django.apps import AppConfig
from django.core.checks import register


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "common"
    verbose_name = "Common (reusable abstract base models)"

    def ready(self):
        from .checks import supabase_configured_when_deployed

        register(supabase_configured_when_deployed)
