from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self):
        # Import so drf-spectacular discovers the OpenApiAuthenticationExtension
        # subclasses (api/schemas.py) when generating the OpenAPI schema.
        from . import schemas  # noqa: F401
