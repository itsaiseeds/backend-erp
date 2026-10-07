"""Custom DRF exception handler that normalises every error response to
``{"detail": "<human-readable message>"}``.

DRF's default handler returns field-level errors as ``{"field": ["msg"]}``
which leaks internal structure to clients.  This handler intercepts those and
flattens them into a single ``detail`` key so the front-end only needs to
read one place.

It also translates Django's own ``ValidationError`` -- what the operations
layer and ``Model.full_clean()`` raise -- into DRF's, so a broken business rule
reaches the caller as a 400 with its message instead of a 500.
"""

from __future__ import annotations

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as _drf_default

logger = logging.getLogger(__name__)

_SERVER_ERROR_MESSAGE = (
    "Something went wrong on our side. Please try again, and contact support if it continues."
)


def _flatten(errors) -> str:
    """Recursively collect every ``ErrorDetail`` / string from a DRF
    error dict and join them into a single human-readable string."""
    parts: list[str] = []
    if isinstance(errors, dict):
        for value in errors.values():
            parts.append(_flatten(value))
    elif isinstance(errors, list):
        for item in errors:
            parts.append(_flatten(item))
    else:
        parts.append(str(errors))
    return " ".join(parts)


def custom_exception_handler(exc, context):
    """Wrap DRF's default handler and normalise the response shape."""
    if isinstance(exc, DjangoValidationError):
        exc = DRFValidationError(exc.messages)

    response = _drf_default(exc, context)

    if response is None and isinstance(exc, DatabaseError):
        # A schema/DB failure is never the caller's to fix and its text names
        # tables and columns: log it, answer with a plain message.
        logger.exception("Database error in %s", context.get("view"))
        return Response({"detail": _SERVER_ERROR_MESSAGE}, status=500)

    if response is not None:
        data = response.data
        # Already in the desired shape — nothing to do.
        if isinstance(data, dict) and "detail" in data and len(data) == 1:
            return response

        # Flatten whatever nested structure DRF produced.
        response.data = {"detail": _flatten(data)}

    return response
