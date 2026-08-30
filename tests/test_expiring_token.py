"""Unit tests for ``ExpiringTokenAuthentication``.

The parent :class:`~rest_framework.authentication.TokenAuthentication` does the
database lookup; these tests stub it to focus purely on the 24h TTL rule -- no
database or live server needed.
"""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from api.authentication import ExpiringTokenAuthentication


def _stub_authentication(monkeypatch: pytest.MonkeyPatch, created) -> SimpleNamespace:
    """Replace the parent's DB lookup; return stubs for user and token."""
    token = SimpleNamespace(created=created, delete=Mock())
    user = SimpleNamespace(is_active=True)
    monkeypatch.setattr(
        TokenAuthentication,
        "authenticate_credentials",
        lambda self, key: (user, token),
    )
    return SimpleNamespace(user=user, token=token)


def test_fresh_token_accepted(monkeypatch: pytest.MonkeyPatch):
    """tests/test_expiring_token.py::test_fresh_token_accepted"""
    stubs = _stub_authentication(monkeypatch, timezone.now())
    auth = ExpiringTokenAuthentication()
    result_user, result_token = auth.authenticate_credentials("abc")
    assert result_user is stubs.user
    assert result_token is stubs.token
    stubs.token.delete.assert_not_called()


def test_expired_token_rejected_and_deleted(monkeypatch: pytest.MonkeyPatch):
    """tests/test_expiring_token.py::test_expired_token_rejected_and_deleted"""
    stubs = _stub_authentication(
        monkeypatch,
        timezone.now() - timedelta(hours=settings.TOKEN_TTL_HOURS + 2),
    )
    auth = ExpiringTokenAuthentication()
    with pytest.raises(AuthenticationFailed, match="expired"):
        auth.authenticate_credentials("abc")
    stubs.token.delete.assert_called_once_with()


def test_token_just_under_ttl_still_accepted(monkeypatch: pytest.MonkeyPatch):
    """tests/test_expiring_token.py::test_token_just_under_ttl_still_accepted"""
    stubs = _stub_authentication(
        monkeypatch,
        timezone.now() - timedelta(hours=settings.TOKEN_TTL_HOURS - 1),
    )
    auth = ExpiringTokenAuthentication()
    result_user, result_token = auth.authenticate_credentials("abc")
    assert result_user is stubs.user
    assert result_token is stubs.token
    stubs.token.delete.assert_not_called()
