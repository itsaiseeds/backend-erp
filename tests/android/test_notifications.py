"""Android push-notification endpoints: device registration and the inbox.

``POST devices/register``, ``GET notifications``, ``POST notification/<id>/read``,
``POST notifications/read-all`` and the logout clean-up. What *triggers* a
notification is covered in ``tests/test_admin_order_lifecycle_api.py``; the FCM
call itself in ``tests/test_push.py``. Authentication and role gating are proven
once in ``tests/test_view_contracts.py``.
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.models import City, Notification, PushDevice, State
from authentication.models import SalesPerson
from tests.android.common import AndroidApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"
REGISTER_URL = "/android/api/v1/devices/register"
LIST_URL = "/android/api/v1/notifications"
READ_URL = "/android/api/v1/notification/{id}/read"
READ_ALL_URL = "/android/api/v1/notifications/read-all"
LOGOUT_URL = "/android/api/v1/auth/logout"


class AndroidNotificationApiTest(AndroidApiTestCase):
    """tests/android/test_notifications.py::AndroidNotificationApiTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        city = City.objects.get(
            name="Surat", state=State.objects.get(name="Gujarat", country__name="India")
        )
        cls.me = cls._sales_person("9000000701", "Me", city, superuser)
        cls.other = cls._sales_person("9000000702", "Other", city, superuser)

    @staticmethod
    def _sales_person(phone, name, city, superuser):
        user = User.objects.create_user(
            phone_number=phone,
            name=name,
            is_verified=True,
            created_by=superuser,
            verified_by=superuser,
        )
        SalesPerson.objects.create(user=user, city=city, created_by=superuser)
        return user

    def setUp(self):
        super().setUp()
        self.login_as(self.me)

    def _notify(self, user, title="Order confirmed", *, read=False):
        notification = Notification.objects.create(
            recipient=user,
            event_type="ORDER_CONFIRMED",
            title=title,
            body="ORD-X was confirmed.",
            data={"order_public_id": "ORD-X"},
        )
        if read:
            notification.read_at = notification.created_at
            notification.save(update_fields=["read_at"])
        return notification

    # -- device registration --------------------------------------------------

    def test_register_stores_the_token_for_the_caller(self):
        """tests/android/test_notifications.py::AndroidNotificationApiTest::test_register_stores_the_token_for_the_caller"""
        response = self.client.post(
            REGISTER_URL, {"fcm_token": "tok-1", "app_version": "1.4.0"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        device = PushDevice.objects.get(fcm_token="tok-1")
        self.assertEqual(device.user, self.me)
        self.assertEqual(device.app_version, "1.4.0")

    def test_registering_twice_keeps_one_row(self):
        """tests/android/test_notifications.py::AndroidNotificationApiTest::test_registering_twice_keeps_one_row"""
        for version in ("1.0.0", "1.1.0"):
            self.client.post(
                REGISTER_URL, {"fcm_token": "tok-1", "app_version": version}, format="json"
            )

        self.assertEqual(PushDevice.objects.count(), 1)
        self.assertEqual(PushDevice.objects.get().app_version, "1.1.0")

    def test_a_token_moves_to_whoever_registers_it_last(self):
        """A shared phone: the next person to log in owns its token.

        tests/android/test_notifications.py::AndroidNotificationApiTest::test_a_token_moves_to_whoever_registers_it_last
        """
        PushDevice.objects.create(user=self.other, fcm_token="shared")

        self.client.post(REGISTER_URL, {"fcm_token": "shared"}, format="json")

        self.assertEqual(PushDevice.objects.get(fcm_token="shared").user, self.me)

    def test_register_requires_a_token(self):
        """tests/android/test_notifications.py::AndroidNotificationApiTest::test_register_requires_a_token"""
        response = self.client.post(REGISTER_URL, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_forgets_the_callers_devices_only(self):
        """tests/android/test_notifications.py::AndroidNotificationApiTest::test_logout_forgets_the_callers_devices_only"""
        PushDevice.objects.create(user=self.me, fcm_token="mine")
        PushDevice.objects.create(user=self.other, fcm_token="theirs")

        response = self.client.post(LOGOUT_URL)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(list(PushDevice.objects.values_list("fcm_token", flat=True)), ["theirs"])

    # -- inbox ----------------------------------------------------------------

    def test_the_inbox_lists_only_my_notifications_newest_first(self):
        """tests/android/test_notifications.py::AndroidNotificationApiTest::test_the_inbox_lists_only_my_notifications_newest_first"""
        self._notify(self.me, "first")
        second = self._notify(self.me, "second")
        self._notify(self.other, "not mine")
        # Windows' clock is coarse enough to give both rows the same created_at.
        Notification.objects.filter(pk=second.pk).update(
            created_at=second.created_at + timedelta(seconds=1)
        )

        response = self.client.get(LIST_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([n["title"] for n in response.data["results"]], ["second", "first"])
        self.assertEqual(response.data["results"][0]["data"], {"order_public_id": "ORD-X"})
        self.assertEqual(response.data["results"][0]["screen"], "order_detail")
        self.assertFalse(response.data["results"][0]["is_read"])

    def test_the_inbox_filters_by_read_state(self):
        """tests/android/test_notifications.py::AndroidNotificationApiTest::test_the_inbox_filters_by_read_state"""
        self._notify(self.me, "seen", read=True)
        self._notify(self.me, "new")

        unread = self.client.get(LIST_URL, {"is_read": "false"})
        read = self.client.get(LIST_URL, {"is_read": "true"})
        both = self.client.get(LIST_URL, {"is_read": "true,false"})
        bad = self.client.get(LIST_URL, {"is_read": "maybe"})

        self.assertEqual([n["title"] for n in unread.data["results"]], ["new"])
        self.assertEqual([n["title"] for n in read.data["results"]], ["seen"])
        self.assertEqual(both.data["total_count"], 2)
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mark_read_marks_one_notification(self):
        """tests/android/test_notifications.py::AndroidNotificationApiTest::test_mark_read_marks_one_notification"""
        target = self._notify(self.me, "target")
        untouched = self._notify(self.me, "untouched")

        response = self.client.post(READ_URL.format(id=target.pk))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        target.refresh_from_db()
        untouched.refresh_from_db()
        self.assertIsNotNone(target.read_at)
        self.assertIsNone(untouched.read_at)
        # Marking it again is not an error.
        self.assertEqual(
            self.client.post(READ_URL.format(id=target.pk)).status_code,
            status.HTTP_204_NO_CONTENT,
        )

    def test_someone_elses_notification_reads_as_unknown(self):
        """tests/android/test_notifications.py::AndroidNotificationApiTest::test_someone_elses_notification_reads_as_unknown"""
        theirs = self._notify(self.other)

        response = self.client.post(READ_URL.format(id=theirs.pk))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        theirs.refresh_from_db()
        self.assertIsNone(theirs.read_at)

    def test_read_all_marks_only_my_notifications(self):
        """tests/android/test_notifications.py::AndroidNotificationApiTest::test_read_all_marks_only_my_notifications"""
        mine = [self._notify(self.me), self._notify(self.me)]
        theirs = self._notify(self.other)

        response = self.client.post(READ_ALL_URL)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        for notification in mine:
            notification.refresh_from_db()
            self.assertIsNotNone(notification.read_at)
        theirs.refresh_from_db()
        self.assertIsNone(theirs.read_at)
