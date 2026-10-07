"""Lab testing of inward raw-material lots: the lab tester's verdict decides the lot.

A raw lot is booked in ``Lab Testing`` and held back from stock. A lab tester
records its grow-out test -- plants, female and OT counts, a
comment and, entered by the tester themselves, ``Pass`` or ``Fail`` -- and that
verdict moves the lot::

    Pass  ->  In Use     (counts toward usable raw material from today)
    Fail  ->  Rejected   (counts toward rejected raw material from today)

Both stamp ``effective_date`` with today, exactly as the old manual flip did.
An admin can only send a lot back (``In Use`` / ``Rejected`` -> ``Lab Testing``,
see ``InwardOperations.ALLOWED_RAW_STATUS_TRANSITIONS``); nobody else can move
a lot out of ``Lab Testing``.

**One test per lot.** ``InwardRawMaterial.lab_testing`` is one-to-one: a lot sent
back to the lab keeps its record, ``result`` emptied and the inputs untouched,
and the next verdict **updates that row**.

**Editing.** The tester may correct any input of their record at any time. The
*verdict* is guarded like every other stock move: ``Pass -> Fail`` takes the
lot's kilograms out of the usable pool, so it is refused when bags or sample
packets are already packed from them (``assert_raw_lot_removable``, which
also covers the orders those bags back) -- no figure may go negative.
``Fail -> Pass`` only adds kilograms and is always allowed.

``genetical_impurity = (female + OT) / plants * 100`` and
``grow_out_test = 100 - genetical_impurity`` are computed on read (see
``LabTesting``), never stored.

Every write here goes through ``InwardOperations.update_raw_lot``, so the stock
ledger, the usability guard and the raw-pool locks apply exactly once. Callers
load the lot with :func:`locked_lot_for_test` (or ``locked_raw_lot``) inside
``transaction.atomic``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.http import Http404

from common.models import indian_now

from .InwardOperations import (
    assert_raw_lot_removable,
    inward_raw_material_payload,
    locked_raw_lot,
    raw_status_of,
    status_row_for,
    today,
    update_raw_lot,
)
from .models import (
    InwardRawMaterial,
    InwardRawMaterialStatus,
    LabTesting,
    LabTestResult,
)

if TYPE_CHECKING:
    from authentication.models import User

# What a verdict does to the lot.
RESULT_TO_STATUS = {
    LabTestResult.PASS: InwardRawMaterialStatus.IN_USE,
    LabTestResult.FAIL: InwardRawMaterialStatus.RAW_MATERIAL_REJECTED,
}

# The inputs a tester types; ``result`` is handled separately because it moves the lot.
VALUE_FIELDS = ("number_of_plants", "female_count", "ot_count", "comment")

# The lot columns echoed inside a lab-testing payload (the rest stays on the lot endpoints).
_LOT_FIELDS = ("public_id", "product", "party", "lot_no", "quantity_kg", "status")


# -- Payloads ------------------------------------------------------------------


def lab_testing_payload(test: LabTesting, lot: InwardRawMaterial | None = None) -> dict:
    """Frontend-facing dict for one ``LabTesting`` (``LT-…``) and the lot it tests."""
    lot = lot if lot is not None else test.inward_raw_material
    lot_payload = inward_raw_material_payload(lot)
    return {
        "public_id": test.public_id,
        "number_of_plants": test.number_of_plants,
        "female_count": test.female_count,
        "ot_count": test.ot_count,
        "genetical_impurity": str(test.genetical_impurity),
        "grow_out_test": str(test.grow_out_test),
        "result": test.result,
        "comment": test.comment,
        "tested_by": (
            {"id": test.tested_by_id, "name": test.tested_by.display_name}
            if test.tested_by_id is not None
            else None
        ),
        "tested_at": test.tested_at.isoformat() if test.tested_at is not None else None,
        "inward_raw_material": {field: lot_payload[field] for field in _LOT_FIELDS},
    }


# -- Loading -------------------------------------------------------------------


def locked_lot_for_test(queryset: QuerySet, test_public_id: str) -> InwardRawMaterial:
    """The lot behind ``LT-…``, loaded through ``locked_raw_lot`` (404 when none).

    A soft-deleted lot has no testable record, so its test is a 404 too. Must
    be called inside ``transaction.atomic``.
    """
    lot_public_id = (
        InwardRawMaterial.objects.filter(lab_testing__public_id=test_public_id)
        .values_list("public_id", flat=True)
        .first()
    )
    if lot_public_id is None:
        raise Http404("No LabTesting matches the given query.")
    return locked_raw_lot(queryset, lot_public_id)


# -- Rules ---------------------------------------------------------------------


def _validate(test: LabTesting) -> None:
    """Refuse inputs that would make a figure negative or impossible (400)."""
    test.clean()


def _apply_values(test: LabTesting, values: Mapping[str, object]) -> None:
    for field in VALUE_FIELDS:
        if field in values:
            setattr(test, field, values[field])


def _stamp(test: LabTesting, actor: User) -> None:
    test.tested_by = actor
    test.tested_at = indian_now()


def _assert_lot_matches_result(lot: InwardRawMaterial, test: LabTesting) -> None:
    """A recorded verdict and its lot's status must agree (they only move together)."""
    expected = RESULT_TO_STATUS[LabTestResult(test.result)]
    if raw_status_of(lot) != expected:
        raise ValidationError(
            f"This lot is {raw_status_of(lot).label}, which does not match its "
            f"recorded result ({test.result}); ask an admin to send it back to Lab Testing."
        )


def _move_lot(lot: InwardRawMaterial, result: str, test: LabTesting, actor: User) -> None:
    """Move ``lot`` to the status ``result`` stands for, stamping today as its effective date."""
    update_raw_lot(
        lot,
        {
            "status": status_row_for(RESULT_TO_STATUS[LabTestResult(result)]),
            "effective_date": today(),
            "lab_testing": test,
        },
        actor,
    )


# -- Writes --------------------------------------------------------------------


@transaction.atomic
def submit_lab_test(
    lot: InwardRawMaterial, values: Mapping[str, object], actor: User
) -> LabTesting:
    """Record the verdict on a lot waiting in ``Lab Testing`` and move the lot.

    Creates the lot's ``LabTesting`` on the first test; after an admin sent the
    lot back it overwrites the same row with the new inputs. ``values`` carries
    every input plus ``result``. A lot an accepted return booked is refused,
    as is any lot not in ``Lab Testing``.
    """
    lot.refuse_return_lot_change()
    status = raw_status_of(lot)
    if status != InwardRawMaterialStatus.LAB_TESTING:
        raise ValidationError(
            f"Only a lot in Lab Testing can be tested; this lot is {status.label}."
        )
    return _record(lot, values, actor)


def _record(lot: InwardRawMaterial, values: Mapping[str, object], actor: User) -> LabTesting:
    test = lot.lab_testing or LabTesting(created_by=actor)
    _apply_values(test, values)
    test.result = values["result"]
    _stamp(test, actor)
    _validate(test)
    test.save()
    _move_lot(lot, test.result, test, actor)
    return test


@transaction.atomic
def update_lab_test(
    lot: InwardRawMaterial, values: Mapping[str, object], actor: User
) -> LabTesting:
    """Correct a lab test's inputs, or change its verdict (and so the lot's status).

    * Inputs are always editable.
    * While the lot awaits a re-test (``result`` empty), sending a ``result``
      is the re-test itself: it behaves exactly like :func:`submit_lab_test`.
    * Changing a recorded ``result`` flips the lot ``In Use <-> Rejected``.
      ``Pass -> Fail`` is refused (400) when the lot's kilograms are already
      packed into bags or sample packets; ``Fail -> Pass`` is always allowed.
    """
    test = lot.lab_testing
    if test is None:
        raise Http404("No LabTesting matches the given query.")

    if test.result is None:
        if "result" in values:
            lot.refuse_return_lot_change()
            status = raw_status_of(lot)
            if status != InwardRawMaterialStatus.LAB_TESTING:
                raise ValidationError(
                    f"Only a lot in Lab Testing can be tested; this lot is {status.label}."
                )
            return _record(lot, values, actor)
        _apply_values(test, values)
        _stamp(test, actor)
        _validate(test)
        test.save()
        return test

    _assert_lot_matches_result(lot, test)
    new_result = values.get("result", test.result)
    _apply_values(test, values)
    _stamp(test, actor)
    _validate(test)
    if new_result != test.result:
        if test.result == LabTestResult.PASS:
            # Pass -> Fail takes the lot's kilograms out of the usable pool.
            try:
                assert_raw_lot_removable(lot)
            except ValueError as exc:
                raise ValidationError({"result": str(exc)}) from None
        test.result = new_result
        test.save()
        _move_lot(lot, new_result, test, actor)
    else:
        test.save()
    return test
