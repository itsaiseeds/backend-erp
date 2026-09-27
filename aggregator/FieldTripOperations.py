"""Field-trip lifecycle and farmer-visit helpers for the ``aggregator`` domain.

A sales person plans a trip (PLANNED), a sales admin approves it (APPROVED),
the sales person starts it (IN_PROGRESS), records the farmers they meet, and
ends it (COMPLETED). Which statuses each verb may be applied from lives here,
beside the verb, so the rule holds however the function is reached.

Trips and visits are exposed by their ``public_id`` (``FT-…`` / ``FV-…``);
payloads never include their primary key.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q, QuerySet

from common.models import indian_now

from .models import (
    City,
    Crop,
    FarmerVisit,
    FarmerVisitCrop,
    FarmerVisitProduct,
    FieldTrip,
    Product,
    Status,
    StatusIds,
)

if TYPE_CHECKING:
    from authentication.models import User

ADMIN_EDITABLE_STATUS_CODES = frozenset({StatusIds.PLANNED.name})
OWNER_EDITABLE_STATUS_CODES = frozenset({StatusIds.PLANNED.name, StatusIds.APPROVED.name})
APPROVABLE_STATUS_CODES = frozenset({StatusIds.PLANNED.name})
UNAPPROVABLE_STATUS_CODES = frozenset({StatusIds.APPROVED.name})
STARTABLE_STATUS_CODES = frozenset({StatusIds.APPROVED.name})
ENDABLE_STATUS_CODES = frozenset({StatusIds.IN_PROGRESS.name})
FARMER_VISIT_STATUS_CODES = frozenset({StatusIds.IN_PROGRESS.name})

# The fields an edit may change. Status, approval and the actual start/end
# times belong to their own verbs.
FIELD_TRIP_EDITABLE_FIELDS = ("city", "village", "expected_start_at", "expected_end_at")


def assert_field_trip_status(trip: FieldTrip, allowed: frozenset[str], action: str) -> None:
    """Guard a lifecycle transition on the trip's current status (400 if refused)."""
    code = trip.status_code
    if code not in allowed:
        raise ValidationError(
            {
                "status": (
                    f"Cannot {action} a field trip that is {code}. "
                    f"Allowed: {', '.join(sorted(allowed))}."
                )
            }
        )


def field_trip_queryset() -> QuerySet[FieldTrip]:
    """Every trip with the joins and the visit count a trip payload reads."""
    return FieldTrip.objects.select_related("status", "city", "created_by", "approved_by").annotate(
        farmer_visit_count=Count("farmer_visits", filter=Q(farmer_visits__is_deleted=False))
    )


def farmer_visit_queryset() -> QuerySet[FarmerVisit]:
    """Every visit with the crops and products a visit payload reads."""
    return FarmerVisit.objects.prefetch_related("visit_crops__crop", "visit_products__product")


@transaction.atomic
def create_field_trip(
    *,
    sales_person: User,
    city: City,
    village: str,
    expected_start_at: datetime,
    expected_end_at: datetime,
) -> FieldTrip:
    """Plan a trip. It is born PLANNED and needs a sales admin's approval."""
    trip = FieldTrip(
        city=city,
        village=village,
        expected_start_at=expected_start_at,
        expected_end_at=expected_end_at,
        status=Status.by_id(StatusIds.PLANNED),
        created_by=sales_person,
    )
    trip.full_clean()
    trip.save()
    return trip


def _apply_field_trip_edit(trip: FieldTrip, fields: dict[str, object]) -> list[str]:
    changed = [name for name in FIELD_TRIP_EDITABLE_FIELDS if name in fields]
    for name in changed:
        setattr(trip, name, fields[name])
    return changed


@transaction.atomic
def edit_field_trip_as_admin(trip: FieldTrip, **fields: object) -> FieldTrip:
    """A sales admin corrects a trip -- only before approving it."""
    assert_field_trip_status(trip, ADMIN_EDITABLE_STATUS_CODES, "edit")
    changed = _apply_field_trip_edit(trip, fields)
    trip.full_clean()
    trip.save(update_fields=[*changed, "updated_at"])
    return trip


@transaction.atomic
def edit_field_trip_as_owner(trip: FieldTrip, **fields: object) -> FieldTrip:
    """The sales person changes their own trip before it starts.

    Editing an APPROVED trip withdraws the approval: the trip goes back to
    PLANNED, so no admin's approval ever stands on details they did not see.
    """
    assert_field_trip_status(trip, OWNER_EDITABLE_STATUS_CODES, "edit")
    changed = _apply_field_trip_edit(trip, fields)
    if changed and trip.status_code == StatusIds.APPROVED.name:
        trip.status = Status.by_id(StatusIds.PLANNED)
        trip.approved_by = None
        trip.approved_at = None
        changed += ["status", "approved_by", "approved_at"]
    trip.full_clean()
    trip.save(update_fields=[*changed, "updated_at"])
    return trip


@transaction.atomic
def approve_field_trip(trip: FieldTrip, admin: User) -> FieldTrip:
    """A sales admin approves a planned trip, recording who and when."""
    assert_field_trip_status(trip, APPROVABLE_STATUS_CODES, "approve")
    if not (admin is not None and (admin.is_admin_user or admin.is_superuser)):
        raise PermissionDenied("Field trips can only be approved by a sales admin.")
    trip.status = Status.by_id(StatusIds.APPROVED)
    trip.approved_by = admin
    trip.approved_at = indian_now()
    trip.full_clean()
    trip.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    return trip


@transaction.atomic
def unapprove_field_trip(trip: FieldTrip) -> FieldTrip:
    """Withdraw an approval before the trip starts; it goes back to PLANNED."""
    assert_field_trip_status(trip, UNAPPROVABLE_STATUS_CODES, "unapprove")
    trip.status = Status.by_id(StatusIds.PLANNED)
    trip.approved_by = None
    trip.approved_at = None
    trip.full_clean()
    trip.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    return trip


@transaction.atomic
def start_field_trip(trip: FieldTrip) -> FieldTrip:
    """Start an approved trip now.

    A sales person runs one trip at a time. The owner's trips are locked first
    so two concurrent starts cannot both pass the check; the partial unique
    index ``uniq_fieldtrip_one_in_progress_per_sales_person`` is the backstop.
    """
    assert_field_trip_status(trip, STARTABLE_STATUS_CODES, "start")
    owner_trips = FieldTrip.objects.select_for_update().filter(created_by_id=trip.created_by_id)
    running = (
        owner_trips.filter(status_id=StatusIds.IN_PROGRESS)
        .exclude(id=trip.id)
        .values_list("public_id", flat=True)
        .first()
    )
    if running is not None:
        raise ValidationError(
            {"status": f"Field trip {running} is still in progress; end it first."}
        )
    trip.status = Status.by_id(StatusIds.IN_PROGRESS)
    trip.started_at = indian_now()
    trip.full_clean()
    trip.save(update_fields=["status", "started_at", "updated_at"])
    return trip


@transaction.atomic
def end_field_trip(trip: FieldTrip) -> FieldTrip:
    """End an in-progress trip now."""
    assert_field_trip_status(trip, ENDABLE_STATUS_CODES, "end")
    trip.status = Status.by_id(StatusIds.COMPLETED)
    trip.ended_at = indian_now()
    trip.full_clean()
    trip.save(update_fields=["status", "ended_at", "updated_at"])
    return trip


def delete_field_trip(trip: FieldTrip, actor: User) -> None:
    """Soft delete a trip that has not started (the model refuses any other)."""
    trip.mark_deleted(actor)


@transaction.atomic
def create_farmer_visit(
    trip: FieldTrip,
    *,
    actor: User,
    farmer_name: str,
    contact_number: str,
    land_area_bigha: Decimal,
    crops: Iterable[Crop],
    products: Iterable[Product] = (),
    village: str = "",
) -> FarmerVisit:
    """Record a farmer met on ``trip``, with the crops they grow and our products they use.

    Only while the trip is in progress. ``village`` defaults to the trip's
    village. No ``products`` means the farmer does not use our products.
    """
    assert_field_trip_status(trip, FARMER_VISIT_STATUS_CODES, "record a farmer on")
    unique_crops = list(dict.fromkeys(crops))
    unique_products = list(dict.fromkeys(products))
    if not unique_crops:
        raise ValidationError({"crops": "At least one crop is required."})
    if FarmerVisit.all_objects.filter(field_trip=trip, contact_number=contact_number).exists():
        raise ValidationError(
            {"contact_number": "This contact number is already recorded on this field trip."}
        )

    visit = FarmerVisit(
        field_trip=trip,
        farmer_name=farmer_name,
        contact_number=contact_number,
        village=village.strip() or trip.village,
        land_area_bigha=land_area_bigha,
        created_by=actor,
    )
    visit.full_clean()
    visit.save()
    FarmerVisitCrop.objects.bulk_create(
        FarmerVisitCrop(farmer_visit=visit, crop=crop, created_by=actor) for crop in unique_crops
    )
    FarmerVisitProduct.objects.bulk_create(
        FarmerVisitProduct(farmer_visit=visit, product=product, created_by=actor)
        for product in unique_products
    )
    return visit


def _user_ref(user: User | None) -> dict | None:
    if user is None:
        return None
    return {"id": user.id, "name": user.name, "phone_number": user.phone_number}


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def field_trip_payload(trip: FieldTrip) -> dict:
    """Frontend-facing dict for a trip, keyed by its public id."""
    visit_count = getattr(trip, "farmer_visit_count", None)
    if visit_count is None:
        visit_count = trip.farmer_visits.count()
    return {
        "public_id": trip.public_id,
        "status": trip.status_code,
        "city": {"id": trip.city_id, "name": trip.city.name},
        "village": trip.village,
        "expected_start_at": _isoformat(trip.expected_start_at),
        "expected_end_at": _isoformat(trip.expected_end_at),
        "started_at": _isoformat(trip.started_at),
        "ended_at": _isoformat(trip.ended_at),
        "sales_person": _user_ref(trip.created_by),
        "approved_by": _user_ref(trip.approved_by),
        "approved_at": _isoformat(trip.approved_at),
        "farmer_visit_count": visit_count,
        "created_at": _isoformat(trip.created_at),
    }


def farmer_visit_payload(visit: FarmerVisit) -> dict:
    """Frontend-facing dict for one farmer visit, keyed by its public id."""
    products = [link.product for link in visit.visit_products.all()]
    return {
        "public_id": visit.public_id,
        "farmer_name": visit.farmer_name,
        "contact_number": visit.contact_number,
        "village": visit.village,
        "land_area_bigha": str(visit.land_area_bigha),
        "crops": [{"id": link.crop_id, "name": link.crop.name} for link in visit.visit_crops.all()],
        "uses_our_products": bool(products),
        "products": [{"public_id": p.public_id, "name": p.name} for p in products],
        "created_at": _isoformat(visit.created_at),
    }
