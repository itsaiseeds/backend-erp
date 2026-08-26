from django.contrib import admin
from django.urls import path, re_path

from config.views import flutter_catch_all

urlpatterns = [
    path("admin/", admin.site.urls),
    # Future API routes go here BEFORE the catch-all:
    # path("api/", include("api.urls")),
    re_path(r"^sales-admin(?:/(?P<path>.*))?$", flutter_catch_all),
]
