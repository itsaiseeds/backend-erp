"""Send push notifications through Firebase Cloud Messaging (HTTP v1 API).

Deliberately thin: one ``requests`` call per device, authenticated with a
short-lived OAuth token minted from the service-account key in
``settings.FCM_SERVICE_ACCOUNT_JSON``. ``firebase-admin`` is avoided on
purpose -- it drags in gRPC/Firestore dependencies this does not need.
"""

from __future__ import annotations

import json
import logging
import threading

import requests
from django.conf import settings
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
FCM_TIMEOUT_SECONDS = 10

_credentials: service_account.Credentials | None = None
_credentials_lock = threading.Lock()


def push_configured() -> bool:
    """Whether a service-account key is set, i.e. whether pushes can be sent."""
    return bool(settings.FCM_SERVICE_ACCOUNT_JSON)


def _access_token() -> str:
    """A valid OAuth access token, refreshed when the cached one has expired."""
    global _credentials
    with _credentials_lock:
        if _credentials is None:
            _credentials = service_account.Credentials.from_service_account_info(
                json.loads(settings.FCM_SERVICE_ACCOUNT_JSON), scopes=[FCM_SCOPE]
            )
        if not _credentials.valid:
            _credentials.refresh(GoogleAuthRequest())
        return str(_credentials.token)


def _is_dead_token(response: requests.Response) -> bool:
    """Whether FCM says this token will never work again (app removed, token rotated)."""
    if response.status_code not in (400, 404):
        return False
    try:
        error = response.json().get("error", {})
    except ValueError:
        return False
    if not isinstance(error, dict):
        return False
    if error.get("status") == "NOT_FOUND":
        return True
    # A malformed payload is also INVALID_ARGUMENT; only the token case is dead.
    return error.get("status") == "INVALID_ARGUMENT" and "registration token" in str(
        error.get("message", "")
    )


def send_push(tokens: list[str], title: str, body: str, data: dict[str, str]) -> list[str]:
    """Push one message to each of ``tokens``; return the tokens FCM rejected as dead.

    The caller deletes the returned tokens. A transient failure (network, 5xx)
    is logged and the token is kept, so the next event can still reach it.
    """
    if not tokens:
        return []
    if not push_configured():
        logger.info("FCM_SERVICE_ACCOUNT_JSON is not set; skipping push %r.", title)
        return []

    url = f"https://fcm.googleapis.com/v1/projects/{settings.FCM_PROJECT_ID}/messages:send"
    headers = {"Authorization": f"Bearer {_access_token()}"}
    dead: list[str] = []
    for token in tokens:
        message = {
            "message": {
                "token": token,
                "notification": {"title": title, "body": body},
                "data": data,
                "android": {
                    "priority": "HIGH",
                    "notification": {"channel_id": settings.FCM_ANDROID_CHANNEL_ID},
                },
            }
        }
        try:
            response = requests.post(
                url,
                json=message,  # type: ignore[arg-type]  # mixed-value dict; it is plain JSON
                headers=headers,
                timeout=FCM_TIMEOUT_SECONDS,
            )
        except requests.RequestException:
            logger.exception("FCM request failed.")
            continue
        if response.ok:
            continue
        if _is_dead_token(response):
            dead.append(token)
        else:
            logger.error("FCM rejected a push: %s %s", response.status_code, response.text)
    return dead
