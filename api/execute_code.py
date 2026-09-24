"""Run Python on the server: ``POST /api/execute-code/``, and its UI page.

For ad-hoc inspection and one-off data fixes without a shell on the box. The
body is ``{"code": "<python source>"}``; the code runs in-process with every
Django model in scope by its class name (``Order``, ``Client``, ``User``, ...),
plus ``apps``, ``timezone`` and ``transaction``.

Gated by the ``authentication.execute_python_code`` permission **alone**, whatever
the caller's role (a superuser holds it implicitly). Grant it per user in the
Django admin. Every enum defined next to a model (``StatusIds``, ``StageIds``,
``InwardRawMaterialStatus``, ...) is in scope too. Web session only: it lives
outside ``/api/sales-admin/`` because it is a server tool, not part of the
sales-admin app.

``GET /execute-code/`` (:func:`execute_code_page`) is a minimal browser UI for
it. It rides the same session cookie the sales-admin login sets, so log in at
``/sales-admin/`` first; without the permission the page is a 403.

Execution contract:

* The code runs inside one ``transaction.atomic`` block. It **commits** if the
  code finishes and **rolls back** if it raises -- a half-applied fix never
  lands.
* Each SQL statement is capped at :data:`STATEMENT_TIMEOUT_MS` by
  ``SET LOCAL statement_timeout``. Pure-Python loops are not capped.
* ``print`` writes to a per-request buffer returned as ``stdout``; assign to a
  variable named ``result`` to get its ``repr`` back as ``result``.
* Every run is logged -- who, the code, and the outcome.

The response is always ``200`` once the caller is authorised; ``success`` says
whether the code itself raised, and ``error`` carries the traceback if it did.
"""

from __future__ import annotations

import enum
import functools
import io
import logging
import sys
import time
import traceback

from django.apps import apps
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.db.models import Model
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from .admin import AdminApiView

PERMISSION = "authentication.execute_python_code"
STATEMENT_TIMEOUT_MS = 30_000


class ExecuteCodeRequestSerializer(serializers.Serializer):
    code = serializers.CharField(trim_whitespace=False)


class ExecuteCodeResponseSerializer(serializers.Serializer):
    """Output shape of a run (schema only)."""

    success = serializers.BooleanField()
    stdout = serializers.CharField()
    result = serializers.CharField(allow_null=True)
    error = serializers.CharField(allow_null=True)
    duration_ms = serializers.IntegerField()


# Helpers put in scope next to the models, besides ``print``.
HELPERS: dict[str, object] = {"apps": apps, "timezone": timezone, "transaction": transaction}

# QuerySet methods offered by the editor's autocomplete after ``Model.<manager>.``.
QUERYSET_METHODS = (
    "aggregate", "all", "annotate", "bulk_create", "bulk_update", "count", "create",
    "defer", "delete", "distinct", "earliest", "exclude", "exists", "filter", "first",
    "get", "get_or_create", "in_bulk", "iterator", "last", "latest", "none", "only",
    "order_by", "prefetch_related", "select_for_update", "select_related", "update",
    "update_or_create", "values", "values_list",
)


def _models() -> dict[str, type[Model]]:
    """Every installed model, keyed by class name -- the names code can use."""
    return {model.__name__: model for model in apps.get_models()}


def _enums() -> dict[str, type[enum.Enum]]:
    """Every enum defined next to a model (``StatusIds``, ``InwardRawMaterialStatus``, ...).

    Found by scanning each model's own module, so Django ``TextChoices`` and plain
    ``IntEnum`` mirrors are both picked up without being listed here.
    """
    found: dict[str, type[enum.Enum]] = {}
    for model in apps.get_models():
        module = sys.modules[model.__module__]
        for name, value in vars(module).items():
            if (
                isinstance(value, type)
                and issubclass(value, enum.Enum)
                and value.__module__ == module.__name__
            ):
                found[name] = value
    return found


def _namespace(stdout: io.StringIO) -> dict[str, object]:
    """Globals the submitted code runs with: every model and enum, helpers, ``print``."""
    namespace: dict[str, object] = {**_models(), **_enums()}
    namespace.update(
        HELPERS,
        # Bound to this request's buffer rather than redirecting sys.stdout,
        # which is process-wide and would interleave concurrent requests.
        print=functools.partial(print, file=stdout),
    )
    return namespace


class ExecuteCodeView(AdminApiView):
    """Execute Python on the server (``execute_python_code`` permission only)."""

    required_permission = PERMISSION

    @extend_schema(
        operation_id="execute_code",
        summary="Execute Python code on the server (permission-gated)",
        request=ExecuteCodeRequestSerializer,
        responses={200: ExecuteCodeResponseSerializer},
    )
    def post(self, request: Request):
        serializer = ExecuteCodeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code: str = serializer.validated_data["code"]
        user = request.user

        logging.info(
            "execute-code: user id=%s phone=%s running:\n%s",
            user.id,
            user.phone_number,
            code,
        )

        stdout = io.StringIO()
        namespace = _namespace(stdout)
        error: str | None = None
        started = time.monotonic()
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # SET cannot take a bound parameter; the value is our constant.
                    cursor.execute(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}")
                exec(compile(code, "<execute-code>", "exec"), namespace)  # noqa: S102
        except (Exception, SystemExit):
            error = traceback.format_exc()
        duration_ms = round((time.monotonic() - started) * 1000)

        logging.info(
            "execute-code: user id=%s finished in %sms: %s",
            user.id,
            duration_ms,
            "success" if error is None else "failed (rolled back)",
        )

        return Response(
            {
                "success": error is None,
                "stdout": stdout.getvalue(),
                "result": repr(namespace["result"]) if "result" in namespace else None,
                "error": error,
                "duration_ms": duration_ms,
            }
        )


@ensure_csrf_cookie
def execute_code_page(request: HttpRequest) -> HttpResponse:
    """``GET /execute-code/``: the browser UI for :class:`ExecuteCodeView`.

    Anonymous visitors are sent to the sales-admin login; a logged-in user
    without the permission gets a 403, the same rule the API applies.
    """
    if not request.user.is_authenticated:
        return redirect("/sales-admin/")
    if not request.user.has_perm(PERMISSION):
        raise PermissionDenied
    return render(
        request,
        "api/execute_code.html",
        {"api_url": reverse("execute-code"), "catalogue": _completion_catalogue()},
    )


def _completion_catalogue() -> dict[str, object]:
    """What the page's autocomplete offers, built from the real execution scope.

    Derived from :func:`_models` and :data:`HELPERS`, so a new model shows up in
    the editor the moment it is installed -- nothing is listed by hand.
    """
    return {
        "models": {
            name: {
                "app": model._meta.app_label,
                "managers": sorted(manager.name for manager in model._meta.managers),
                "fields": sorted({field.name for field in model._meta.get_fields()}),
            }
            for name, model in sorted(_models().items())
        },
        "enums": {
            name: [member.name for member in enum_class]
            for name, enum_class in sorted(_enums().items())
        },
        "helpers": sorted([*HELPERS, "print"]),
        "queryset_methods": list(QUERYSET_METHODS),
    }

