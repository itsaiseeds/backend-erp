"""Field-trip lifecycle and farmer-visit helpers for the ``aggregator`` domain.

A sales person plans a trip (PLANNED), a sales admin approves it (APPROVED),
the sales person starts it (IN_PROGRESS), records the farmers they meet, and
ends it (COMPLETED). Which statuses each verb may be applied from lives here,
beside the verb, so the rule holds however the function is reached. An approval
decision notifies the sales person who planned the trip.

Trips and visits are exposed by their ``public_id`` (``FT-…`` / ``FV-…``);
payloads never include their primary key.

Farmers, though, are not a model: a ``FarmerVisit`` is a meeting, so the same
farmer met twice is two rows. :func:`farmer_queryset` and
:func:`farmer_payload` fold those meetings back into one farmer -- identified by
``contact_number``, carrying their latest visit's details plus everything merged
across every visit -- for lists that must show all farmers, not one trip's.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, F, IntegerField, OuterRef, Q, QuerySet, Subquery, Window
from django.db.models.functions import RowNumber

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
from .NotificationOperations import NotificationEvent as _NE
from .NotificationOperations import notify_field_trip_event

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
    return FarmerVisit.objects.select_related("field_trip").prefetch_related(
        "visit_crops__crop", "visit_products__product"
    )


def farmer_queryset() -> QuerySet[FarmerVisit]:
    """One row per farmer across every trip: their **latest** visit, plus their visit count.

    A farmer is identified by ``contact_number`` -- the one thing a farmer cannot
    be recorded twice under on the same trip -- so repeat meetings are folded
    together on it. The row kept is the latest visit, hence its ``created_at``
    reads as *last visited*, which is what the all-farmers list sorts and
    date-windows on; ``visit_count`` is how many meetings they have in all.
    """
    visits_per_farmer = Subquery(
        FarmerVisit.objects.filter(contact_number=OuterRef("contact_number"))
        .order_by()
        .values("contact_number")
        .annotate(total=Count("pk"))
        .values("total"),
        output_field=IntegerField(),
    )
    return (
        FarmerVisit.objects.annotate(
            visit_rank=Window(
                expression=RowNumber(),
                partition_by=[F("contact_number")],
                order_by=[F("created_at").desc(), F("pk").desc()],
            ),
            visit_count=visits_per_farmer,
        )
        .filter(visit_rank=1)
        .select_related("field_trip__city", "created_by")
    )


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
    notify_field_trip_event(trip, _NE.FIELD_TRIP_APPROVED, actor=admin)
    return trip


@transaction.atomic
def unapprove_field_trip(trip: FieldTrip, admin: User) -> FieldTrip:
    """Withdraw an approval before the trip starts; it goes back to PLANNED.

    ``admin`` is who withdrew it -- the sales person who planned the trip is
    notified of the decision, so it is recorded with the trip's history.
    """
    assert_field_trip_status(trip, UNAPPROVABLE_STATUS_CODES, "unapprove")
    trip.status = Status.by_id(StatusIds.PLANNED)
    trip.approved_by = None
    trip.approved_at = None
    trip.full_clean()
    trip.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    notify_field_trip_event(trip, _NE.FIELD_TRIP_UNAPPROVED, actor=admin)
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
    is_lead: bool = False,
) -> FarmerVisit:
    """Record a farmer met on ``trip``, with the crops they grow and our products they use.

    Only while the trip is in progress. ``village`` defaults to the trip's
    village. No ``products`` means the farmer does not use our products.
    """
    assert_field_trip_status(trip, FARMER_VISIT_STATUS_CODES, "record a farmer on")
    if FarmerVisit.all_objects.filter(field_trip=trip, contact_number=contact_number).exists():
        raise ValidationError(
            {"contact_number": "This contact number is already recorded on this field trip."}
        )
    return _create_visit(
        trip,
        actor=actor,
        farmer_name=farmer_name,
        contact_number=contact_number,
        village=village.strip() or trip.village,
        land_area_bigha=land_area_bigha,
        crops=crops,
        products=products,
        is_lead=is_lead,
    )


@transaction.atomic
def create_independent_farmer(
    *,
    actor: User,
    farmer_name: str,
    contact_number: str,
    village: str,
    land_area_bigha: Decimal,
    crops: Iterable[Crop],
    products: Iterable[Product] = (),
    is_lead: bool = False,
) -> FarmerVisit:
    """Record a farmer the sales person entered on their own, outside any field trip.

    One live farmer per contact number per sales person. There is no trip to
    default the village from, so it is required.
    """
    if not village.strip():
        raise ValidationError({"village": "Village is required."})
    if _independent_contact_taken(actor, contact_number):
        raise ValidationError(
            {"contact_number": "You have already recorded a farmer with this contact number."}
        )
    return _create_visit(
        None,
        actor=actor,
        farmer_name=farmer_name,
        contact_number=contact_number,
        village=village.strip(),
        land_area_bigha=land_area_bigha,
        crops=crops,
        products=products,
        is_lead=is_lead,
    )


def _independent_contact_taken(actor: User, contact_number: str, exclude_pk=None) -> bool:
    taken = FarmerVisit.objects.filter(
        field_trip__isnull=True, created_by=actor, contact_number=contact_number
    )
    return taken.exclude(pk=exclude_pk).exists()


def _create_visit(
    trip: FieldTrip | None,
    *,
    actor: User,
    farmer_name: str,
    contact_number: str,
    village: str,
    land_area_bigha: Decimal,
    crops: Iterable[Crop],
    products: Iterable[Product],
    is_lead: bool,
) -> FarmerVisit:
    """Save the row and its crop / product links (``trip`` is ``None`` for an independent farmer)."""
    unique_crops = list(dict.fromkeys(crops))
    unique_products = list(dict.fromkeys(products))
    if not unique_crops:
        raise ValidationError({"crops": "At least one crop is required."})

    visit = FarmerVisit(
        field_trip=trip,
        farmer_name=farmer_name,
        contact_number=contact_number,
        village=village,
        land_area_bigha=land_area_bigha,
        is_lead=is_lead,
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


def _sync_visit_links(
    visit: FarmerVisit, link_model, field: str, wanted: list, actor: User
) -> None:
    """Make the visit's live ``link_model`` rows match ``wanted``.

    Dropped links are soft-deleted and a re-added one is restored, because the
    (visit, target) pair is unique even across soft-deleted rows.
    """
    wanted_ids = {target.pk for target in wanted}
    existing = {
        getattr(link, f"{field}_id"): link
        for link in link_model.all_objects.filter(farmer_visit=visit)
    }
    for target_id, link in existing.items():
        if target_id not in wanted_ids:
            link.mark_deleted(actor)
        elif link.is_deleted:
            link.restore()
    link_model.objects.bulk_create(
        link_model(farmer_visit=visit, created_by=actor, **{field: target})
        for target in wanted
        if target.pk not in existing
    )


@transaction.atomic
def update_farmer_visit(
    visit: FarmerVisit,
    *,
    actor: User,
    farmer_name: str | None = None,
    contact_number: str | None = None,
    village: str | None = None,
    land_area_bigha: Decimal | None = None,
    crops: Iterable[Crop] | None = None,
    products: Iterable[Product] | None = None,
    is_lead: bool | None = None,
) -> FarmerVisit:
    """Correct a recorded farmer; only the fields passed (not ``None``) change.

    Only while the trip is in progress (an independent farmer has no trip, so
    it is always editable). The name, contact number, village and
    crop list are required on a farmer, so none may be made blank or empty;
    ``products=[]`` is fine and records that the farmer does not use our products.
    """
    if not visit.is_independent:
        assert_field_trip_status(visit.field_trip, FARMER_VISIT_STATUS_CODES, "edit a farmer on")
    fields = {
        "farmer_name": farmer_name,
        "contact_number": contact_number,
        "village": village,
        "land_area_bigha": land_area_bigha,
        "is_lead": is_lead,
    }
    changed = [name for name, value in fields.items() if value is not None]
    if changed:
        if contact_number is not None:
            if visit.is_independent:
                if _independent_contact_taken(visit.created_by, contact_number, visit.pk):
                    raise ValidationError(
                        {
                            "contact_number": (
                                "You have already recorded a farmer with this contact number."
                            )
                        }
                    )
            elif (
                FarmerVisit.all_objects.filter(
                    field_trip=visit.field_trip, contact_number=contact_number
                )
                .exclude(pk=visit.pk)
                .exists()
            ):
                raise ValidationError(
                    {
                        "contact_number": (
                            "This contact number is already recorded on this field trip."
                        )
                    }
                )
        for name in changed:
            setattr(visit, name, fields[name])
        visit.full_clean()
        visit.save(update_fields=[*changed, "updated_at"])
    if crops is not None:
        unique_crops = list(dict.fromkeys(crops))
        if not unique_crops:
            raise ValidationError({"crop_ids": "At least one crop is required."})
        _sync_visit_links(visit, FarmerVisitCrop, "crop", unique_crops, actor)
    if products is not None:
        unique_products = list(dict.fromkeys(products))
        _sync_visit_links(visit, FarmerVisitProduct, "product", unique_products, actor)
    return visit


def delete_independent_farmer(visit: FarmerVisit, actor: User) -> None:
    """Soft-delete a farmer recorded outside any trip."""
    visit.mark_deleted(actor)


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
        "is_lead": visit.is_lead,
        "field_trip_public_id": visit.field_trip.public_id if visit.field_trip_id else None,
        "crops": [{"id": link.crop_id, "name": link.crop.name} for link in visit.visit_crops.all()],
        "uses_our_products": bool(products),
        "products": [{"public_id": p.public_id, "name": p.name} for p in products],
        "created_at": _isoformat(visit.created_at),
    }


def farmer_visit_export_payload(visit: FarmerVisit) -> dict:
    """A visit payload plus the trip it was recorded on and the sales person who met the farmer."""
    trip = visit.field_trip
    return {
        **farmer_visit_payload(visit),
        "field_trip": (
            {
                "public_id": trip.public_id,
                "village": trip.village,
                "city": {"id": trip.city_id, "name": trip.city.name},
            }
            if trip is not None
            else None
        ),
        "sales_person": _user_ref(trip.created_by if trip is not None else visit.created_by),
    }


def farmer_visits_by_contact(contacts: Iterable[str]) -> dict[str, list[FarmerVisit]]:
    """Every live visit of each farmer in ``contacts``, newest first, keyed by contact number.

    The one query a page of farmers needs: their crops, products and meetings are
    read off these rows rather than off the farmer row, which is one visit.
    """
    visits = (
        FarmerVisit.objects.filter(contact_number__in=list(contacts))
        .select_related("field_trip", "created_by")
        .prefetch_related("visit_crops__crop", "visit_products__product")
        .order_by("-created_at", "-pk")
    )
    grouped: dict[str, list[FarmerVisit]] = {}
    for visit in visits:
        grouped.setdefault(visit.contact_number, []).append(visit)
    return grouped


def _by_name(refs: dict) -> list[dict]:
    """``{id: name}`` as a name-ordered list of ``{id, name}`` refs."""
    return [
        {"id": ref_id, "name": refs[ref_id]} for ref_id in sorted(refs, key=lambda i: (refs[i], i))
    ]


def farmer_payload(latest: FarmerVisit, visits: Sequence[FarmerVisit]) -> dict:
    """One farmer: their latest visit's details, merged across every visit they have.

    ``latest`` is the farmer's row from :func:`farmer_queryset` and ``visits``
    every visit of theirs, newest first (see :func:`farmer_visits_by_contact`).
    The latest visit speaks for the name, village, city and land area -- what we
    were told most recently -- while the crops, products and meeting history are
    the union over all of them, so nothing a farmer was ever recorded as is lost.
    """
    crops = {link.crop_id: link.crop.name for visit in visits for link in visit.visit_crops.all()}
    products = {
        link.product.public_id: link.product.name
        for visit in visits
        for link in visit.visit_products.all()
    }
    sales_people = {visit.created_by_id: visit.created_by.display_name for visit in visits}
    return {
        "contact_number": latest.contact_number,
        "farmer_name": latest.farmer_name,
        "village": latest.village,
        "city": (
            {"id": latest.field_trip.city_id, "name": latest.field_trip.city.name}
            if latest.field_trip_id
            else None
        ),
        "land_area_bigha": str(latest.land_area_bigha),
        "is_lead": latest.is_lead,
        "crops": _by_name(crops),
        "uses_our_products": bool(products),
        "products": [
            {"public_id": public_id, "name": products[public_id]}
            for public_id in sorted(products, key=lambda p: (products[p], p))
        ],
        "visit_count": len(visits),
        "last_visited_at": _isoformat(visits[0].created_at),
        "sales_people": _by_name(sales_people),
        "visits": [
            {
                "public_id": visit.public_id,
                "field_trip_public_id": visit.field_trip.public_id if visit.field_trip_id else None,
                "created_at": _isoformat(visit.created_at),
            }
            for visit in visits
        ],
    }
