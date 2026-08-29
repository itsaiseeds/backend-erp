from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from api.permissions import IsSuperUser
from config.views import flutter_catch_all

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    # Auto-generated API docs for the frontend (Flutter) team — superuser only.
    path(
        "api/schema/",
        SpectacularAPIView.as_view(permission_classes=[IsSuperUser]),
        name="schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            permission_classes=[IsSuperUser], url_name="schema"
        ),
        name="swagger-ui",
    ),
    re_path(r"^sales-admin(?:/(?P<path>.*))?$", flutter_catch_all),
]
