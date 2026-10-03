"""The FCM sender: which responses mean a token is dead.

The network is never touched: ``requests.post`` and the OAuth token are patched.

tests/test_push.py
"""

from __future__ import annotations

from unittest import mock

import requests
from django.test import SimpleTestCase, override_settings

from common.push import send_push

SERVICE_ACCOUNT = '{"type": "service_account"}'


def _response(status_code: int, payload: dict[str, object] | None = None) -> mock.Mock:
    response = mock.Mock(spec=requests.Response)
    response.status_code = status_code
    response.ok = status_code < 400
    response.json.return_value = payload or {}
    response.text = str(payload)
    return response


@override_settings(FCM_SERVICE_ACCOUNT_JSON=SERVICE_ACCOUNT, FCM_PROJECT_ID="demo")
class SendPushTest(SimpleTestCase):
    """tests/test_push.py::SendPushTest"""

    def setUp(self):
        token = mock.patch("common.push._access_token", return_value="oauth")
        token.start()
        self.addCleanup(token.stop)

    def _post(self, *responses):
        patcher = mock.patch("common.push.requests.post", side_effect=list(responses))
        self.post = patcher.start()
        self.addCleanup(patcher.stop)

    def test_sends_one_message_per_token_with_title_body_and_data(self):
        """tests/test_push.py::SendPushTest::test_sends_one_message_per_token_with_title_body_and_data"""
        self._post(_response(200), _response(200))

        dead = send_push(["a", "b"], "Hi", "There", {"order_public_id": "ORD-1"})

        self.assertEqual(dead, [])
        self.assertEqual(self.post.call_count, 2)
        url = self.post.call_args.args[0]
        self.assertEqual(url, "https://fcm.googleapis.com/v1/projects/demo/messages:send")
        message = self.post.call_args.kwargs["json"]["message"]
        self.assertEqual(message["token"], "b")
        self.assertEqual(message["notification"], {"title": "Hi", "body": "There"})
        self.assertEqual(message["data"], {"order_public_id": "ORD-1"})
        self.assertEqual(self.post.call_args.kwargs["headers"], {"Authorization": "Bearer oauth"})

    def test_an_unregistered_token_is_reported_dead(self):
        """tests/test_push.py::SendPushTest::test_an_unregistered_token_is_reported_dead"""
        self._post(_response(404, {"error": {"status": "NOT_FOUND"}}), _response(200))

        self.assertEqual(send_push(["gone", "ok"], "t", "b", {}), ["gone"])

    def test_a_malformed_token_is_dead_but_a_malformed_payload_is_not(self):
        """tests/test_push.py::SendPushTest::test_a_malformed_token_is_dead_but_a_malformed_payload_is_not"""
        bad_token = {
            "error": {
                "status": "INVALID_ARGUMENT",
                "message": "The registration token is not a valid FCM registration token",
            }
        }
        bad_payload = {"error": {"status": "INVALID_ARGUMENT", "message": "Invalid JSON payload"}}
        self._post(_response(400, bad_token), _response(400, bad_payload))

        self.assertEqual(send_push(["x", "y"], "t", "b", {}), ["x"])

    def test_a_transient_failure_keeps_the_token(self):
        """tests/test_push.py::SendPushTest::test_a_transient_failure_keeps_the_token"""
        self._post(_response(503, {"error": {"status": "UNAVAILABLE"}}), requests.Timeout())

        self.assertEqual(send_push(["a", "b"], "t", "b", {}), [])
        self.assertEqual(self.post.call_count, 2)

    def test_no_tokens_means_no_requests(self):
        """tests/test_push.py::SendPushTest::test_no_tokens_means_no_requests"""
        self._post()

        self.assertEqual(send_push([], "t", "b", {}), [])
        self.post.assert_not_called()


class UnconfiguredPushTest(SimpleTestCase):
    """tests/test_push.py::UnconfiguredPushTest"""

    @override_settings(FCM_SERVICE_ACCOUNT_JSON="")
    def test_without_a_service_account_nothing_is_sent(self):
        """tests/test_push.py::UnconfiguredPushTest::test_without_a_service_account_nothing_is_sent"""
        with mock.patch("common.push.requests.post") as post:
            self.assertEqual(send_push(["a"], "t", "b", {}), [])

        post.assert_not_called()
