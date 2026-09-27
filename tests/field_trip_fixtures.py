"""Shared fixtures for the field-trip tests.

Two sales people, one sales admin and the seeded geography / crops / products,
plus a helper that walks a trip to any lifecycle status through the operations
layer -- so each test module asserts behaviour, not setup.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model

from aggregator import FieldTripOperations as ops
from aggregator.models import City, Crop, FarmerVisit, FieldTrip, Product
from aggregator.models.Status import StatusIds
from authentication.models import Admin, SalesPerson
from common.models import indian_now

User = get_user_model()

SUPERUSER_PHONE = "9999999999"


class FieldTripFixtures:
    """Mixed into a ``DMLTestCase`` subclass; call from ``setUpTestData``."""

    @classmethod
    def set_up_field_trip_fixtures(cls) -> None:
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        cls.city = City.objects.get(name="Surat")
        cls.other_city = City.objects.get(name="Ahmedabad")
        # Seeded in dml.sql: Castor / Bajari, and one product of each.
        cls.castor = Crop.objects.get(name="Castor")
        cls.bajari = Crop.objects.get(name="Bajari")
        cls.castor_seed = Product.objects.get(crop=cls.castor)
        cls.bajari_seed = Product.objects.get(crop=cls.bajari)

        cls.sales_person = cls._sales_person("9000000801", "Sales One")
        cls.other_sales_person = cls._sales_person("9000000802", "Sales Two")
        cls.admin_user = User.objects.create_user(
            phone_number="9000000803",
            name="Trip Admin",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(user=cls.admin_user, created_by=cls.superuser)

    @classmethod
    def _sales_person(cls, phone: str, name: str):
        user = User.objects.create_user(
            phone_number=phone,
            name=name,
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        SalesPerson.objects.create(user=user, city=cls.city, created_by=cls.superuser)
        return user

    def make_trip(
        self,
        *,
        owner=None,
        status: StatusIds = StatusIds.PLANNED,
        city=None,
        village: str = "Kamrej",
        starts_in_days: int = 1,
    ) -> FieldTrip:
        """A trip walked to ``status`` through the real transitions."""
        start = indian_now() + timedelta(days=starts_in_days)
        trip = ops.create_field_trip(
            sales_person=owner or self.sales_person,
            city=city or self.city,
            village=village,
            expected_start_at=start,
            expected_end_at=start + timedelta(hours=8),
        )
        steps = [
            (StatusIds.APPROVED, lambda: ops.approve_field_trip(trip, self.admin_user)),
            (StatusIds.IN_PROGRESS, lambda: ops.start_field_trip(trip)),
            (StatusIds.COMPLETED, lambda: ops.end_field_trip(trip)),
        ]
        for step_status, step in steps:
            if status < step_status:
                break
            step()
        return trip

    def make_visit(
        self,
        trip: FieldTrip,
        *,
        contact_number: str = "9876500001",
        crops=None,
        products=(),
        land_area_bigha: str = "2.5",
    ) -> FarmerVisit:
        return ops.create_farmer_visit(
            trip,
            actor=trip.created_by,
            farmer_name="Ramesh Patel",
            contact_number=contact_number,
            land_area_bigha=Decimal(land_area_bigha),
            crops=crops or [self.castor],
            products=products,
        )
