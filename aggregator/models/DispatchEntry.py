from datetime import date

from django.core.exceptions import ValidationError
from django.db import connection, models, transaction
from django.utils import timezone

from authentication.validators import validate_phone_number
from common.models import (
    PrefixedPublicIdModel,
    SoftDeletedModel,
    TimeStampedModel,
)

# The challan number: a dated serial, ``YYYYMMDD-XXXX``, restarting at 0001
# every IST day -- what a client quotes on the phone, where the random ``DE-…``
# public id is unreadable aloud and says nothing about when the goods left.
#
# Derived from ``dispatched_at`` in ``DispatchEntry.save()`` rather than passed
# in, so an admin editing that timestamp cannot leave the two disagreeing.
CHALLAN_NUMBER_SEQUENCE_DIGITS = 4
CHALLAN_NUMBER_MAX_SEQUENCE = 10**CHALLAN_NUMBER_SEQUENCE_DIGITS - 1
# Arbitrary but fixed: the ``classid`` half of the per-day advisory lock key, so
# these locks cannot collide with any other advisory lock the app might take.
CHALLAN_DAY_LOCK_NAMESPACE = 4201


def challan_day_prefix(day: date) -> str:
    """The ``YYYYMMDD-`` that every challan number for ``day`` starts with."""
    return f"{day:%Y%m%d}-"


def _lock_challan_day(day: date) -> None:
    """Serialise challan numbering for ``day`` until this transaction ends.

    ``next_challan_number`` reads the day's highest number and adds one, so two
    concurrent dispatches would otherwise both read the same maximum and pick
    the same number. The row-lock helpers in ``InventoryOperations`` cannot help
    here: they lock a parent row that always exists, and on the *first* dispatch
    of a day there is no row to lock at all -- the race is a phantom read, which
    ``select_for_update`` does not prevent. An advisory lock is the row-less
    equivalent, and it blocks only other dispatches being numbered for the same
    day.

    The key is derived from the date itself so every process agrees on it
    (Python's ``hash`` is salted per process and would not). ``xact`` locks
    release on commit or rollback, so this must run inside a transaction --
    in autocommit it would be dropped before the read it is protecting.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_xact_lock(%s, %s)",
            [CHALLAN_DAY_LOCK_NAMESPACE, int(f"{day:%Y%m%d}")],
        )


def next_challan_number(day: date) -> str:
    """The next free challan number for ``day``. Must run inside a transaction.

    The highest existing number **plus one**, not the day's row count. Counting
    breaks as soon as an entry leaves a day -- which re-dispatching onto a later
    day does: if today held 0001-0003 and 0002 moved to tomorrow, a count would
    hand out 0003 again, which a live entry still holds. Taking the maximum
    cannot: a row that moved took its number with it, and a soft-deleted row
    keeps its number reserved. The cost is gaps, which is the right trade --
    a number already quoted to a client must never mean something else.

    Read through ``all_objects`` so soft-deleted entries still count, and keyed
    on the numbers themselves rather than on ``dispatched_at``, because the
    invariant being protected is that no two entries share a number. That stays
    true even for an entry whose timestamp has just moved and whose number has
    not been rewritten yet.

    Because the sequence is zero-padded to a fixed width, the lexicographic
    maximum is the numeric one -- so one string column is the whole index.
    """
    _lock_challan_day(day)
    prefix = challan_day_prefix(day)
    highest = DispatchEntry.all_objects.filter(
        challan_number__startswith=prefix
    ).aggregate(models.Max("challan_number"))["challan_number__max"]
    sequence = int(highest.removeprefix(prefix)) + 1 if highest else 1
    if sequence > CHALLAN_NUMBER_MAX_SEQUENCE:
        raise ValidationError(
            {
                "challan_number": (
                    f"More than {CHALLAN_NUMBER_MAX_SEQUENCE} dispatches have been "
                    f"numbered for {day:%Y-%m-%d}; the challan number has no room "
                    "for another."
                )
            }
        )
    return f"{prefix}{sequence:0{CHALLAN_NUMBER_SEQUENCE_DIGITS}d}"


class DispatchEntry(PrefixedPublicIdModel, TimeStampedModel, SoftDeletedModel):
    """The challan record for one order or custom order: what left, to whom, on what.

    Exactly one of ``order`` / ``custom_order`` is set
    (``ck_dispatchentry_one_order``). A custom order's lines are loose packets,
    so its ``DispatchEntryItem`` rows name a product and packet weight instead of
    a packaging; everything else about the challan is the same.

    Created by ``dispatch-order`` alongside the ``DispatchDetails`` /
    ``PrivateDispatchDetails`` row, one per order. Where those two tables record
    *the dispatch*, this records *the challan*: the same journey plus the things
    a printed challan needs and the order does not carry -- a per-line lot
    number (``DispatchEntryItem``) and a frozen snapshot of the receiver.

    The receiver fields are a **snapshot**, not a view. A client's primary
    contact or address may change next week; the challan that went out with the
    goods must keep saying what it said, so the address and the contact are
    copied in at dispatch time rather than read through the client.

    ``dispatch_details`` links the transporter row when there is one. Null means
    a private (own-vehicle) dispatch -- ``PrivateDispatchDetails`` has no LR
    number, and everything else it holds is already snapshotted here, so there
    is no second FK; ``entry.order.private_dispatch_details`` reaches it.

    ``lr_number`` is deliberately *not* a column: it is the transporter's, it
    lives on ``DispatchDetails``, and duplicating it would let the two drift.

    Re-dispatching an order (revert, then dispatch again) updates this row in
    place rather than making a second one, so ``DE-…`` names the order's challan
    for as long as the order lives.
    """

    public_id_prefix = "DE-"

    challan_number = models.CharField(
        "challan number",
        max_length=13,  # YYYYMMDD-XXXX
        unique=True,
        db_index=True,
        # ``editable=False, blank=True`` for the same reason as ``public_id``:
        # ``DispatchOperations._upsert_entry`` calls ``full_clean()`` *before*
        # ``save()``, and ``full_clean`` skips non-editable fields -- so a number
        # not yet assigned does not fail validation. It also skips
        # ``validate_unique``, leaving the DB index as the real guarantee.
        editable=False,
        blank=True,
        help_text=(
            "The dated serial a client quotes: YYYYMMDD-XXXX, restarting at 0001 "
            "each IST day. Derived from dispatched_at, never typed."
        ),
    )

    order = models.OneToOneField(
        "aggregator.Order",
        verbose_name="order",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="dispatch_entry",
    )
    custom_order = models.OneToOneField(
        "aggregator.CustomOrder",
        verbose_name="custom order",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="dispatch_entry",
    )
    dispatch_details = models.ForeignKey(
        "aggregator.DispatchDetails",
        verbose_name="dispatch details",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="dispatch_entries",
        help_text=(
            "The transporter row this challan was raised against, and where its "
            "LR number lives. Null for a private (own-vehicle) dispatch."
        ),
    )
    client = models.ForeignKey(
        "aggregator.Client",
        verbose_name="client",
        on_delete=models.PROTECT,
        related_name="dispatch_entries",
    )
    client_address = models.ForeignKey(
        "aggregator.Address",
        verbose_name="client address",
        on_delete=models.PROTECT,
        related_name="dispatch_entries",
        help_text="The order's delivery address as it stood at dispatch time.",
    )
    contact_name = models.CharField("contact name", max_length=255, blank=True)
    contact_number = models.CharField(
        "contact number",
        max_length=10,
        blank=True,
        validators=[validate_phone_number],
    )
    dispatched_at = models.DateTimeField(
        "dispatched at",
        help_text=(
            "When this consignment was recorded. Re-stamped on a re-dispatch, "
            "unlike ``created_at``, which stays at the first one."
        ),
    )
    from_city = models.ForeignKey(
        "aggregator.City",
        verbose_name="from city",
        on_delete=models.PROTECT,
        related_name="dispatch_entries_from",
    )
    to_city = models.ForeignKey(
        "aggregator.City",
        verbose_name="to city",
        on_delete=models.PROTECT,
        related_name="dispatch_entries_to",
    )
    # Blank whenever the dispatch they were snapshotted from left them blank,
    # which an agency dispatch may (see ``DispatchDetails``). Required there
    # would make the snapshot unwritable for a dispatch the API accepted.
    vehicle_number = models.CharField("vehicle number", max_length=32, blank=True)
    driver_name = models.CharField("driver name", max_length=255, blank=True)
    driver_number = models.CharField(
        "driver number",
        max_length=10,
        blank=True,
        validators=[validate_phone_number],
    )

    class Meta:
        verbose_name = "dispatch entry"
        verbose_name_plural = "dispatch entries"
        ordering = ["-dispatched_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(order__isnull=False, custom_order__isnull=True)
                    | models.Q(order__isnull=True, custom_order__isnull=False)
                ),
                name="ck_dispatchentry_one_order",
            ),
        ]

    def save(self, *args, **kwargs):
        """Keep ``challan_number`` on the IST day ``dispatched_at`` names.

        Derived here rather than in ``DispatchOperations`` so **every** writer is
        covered: the dispatch path, a re-dispatch, and a Django admin edit of
        ``dispatched_at`` (which is a plain editable field on
        ``DispatchEntryAdmin``). This mirrors how ``public_id`` is generated in
        ``PrefixedPublicIdModel.save`` -- the project derives fields in ``save``
        and has no signals.

        A number is kept while it still names the right day, so a re-dispatch on
        the same day stays on the number already quoted to the client, and only a
        move to another day earns a fresh one. The old day's number is not
        reused: see ``next_challan_number``.
        """
        prefix = challan_day_prefix(timezone.localtime(self.dispatched_at).date())
        if self.challan_number.startswith(prefix):
            super().save(*args, **kwargs)
            return

        # A new entry, or ``dispatched_at`` has moved to a different day.
        # ``transaction.atomic`` is for the advisory lock, not the write: an
        # ``xact`` lock taken in autocommit would be released before the read it
        # protects. Both real callers (``sync_dispatch_entry``, the admin change
        # form) are already atomic, so this is usually just a savepoint.
        with transaction.atomic():
            self.challan_number = next_challan_number(
                timezone.localtime(self.dispatched_at).date()
            )
            # A partial save that did not list the column would leave the new
            # number in memory only -- ``restore()`` and the soft delete both
            # save four columns and nothing else.
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = [*update_fields, "challan_number"]
            super().save(*args, **kwargs)

    def __str__(self):
        return self.public_id or "Dispatch entry"

    @property
    def dispatch_date(self):
        """The date printed on the challan: the IST day the goods left.

        Converted to local time first: a timestamp read back from the database
        is UTC, whose date is still yesterday between midnight and 05:30 IST.
        """
        return timezone.localtime(self.dispatched_at).date()

    @property
    def is_private(self):
        """True when the goods went on our own vehicle (no transporter, no LR)."""
        return not self.dispatch_details_id

    @property
    def lr_number(self):
        """The transporter's consignment note, read through rather than stored.

        Blank on a private dispatch (there is nothing to read) and on an agency
        dispatch whose LR has not been recorded yet.
        """
        return self.dispatch_details.lr_number if self.dispatch_details_id else ""

    @property
    def total_amount(self):
        return sum((item.line_total for item in self.items.all()), 0)

    @property
    def source_order(self):
        """Whichever order this challan belongs to -- an Order or a CustomOrder."""
        return self.order if self.order_id else self.custom_order

    @property
    def total_packets(self):
        return sum((item.total_packets for item in self.items.all()), 0)

    def clean(self):
        super().clean()
        errors = {}

        if bool(self.order_id) == bool(self.custom_order_id):
            errors["order"] = "A dispatch entry names exactly one order or custom order."

        source = self.source_order if (self.order_id or self.custom_order_id) else None
        if source is not None and self.client_id and source.client_id != self.client_id:
            errors["client"] = "A dispatch entry must name the order's own client."

        # No independent "belongs to the client" check for ``client_address``:
        # it is always copied from the order's own ``delivery_address``
        # (``DispatchOperations._upsert_entry``), which was already validated
        # against the client's addresses when the order itself was booked (see
        # ``Order.client_link_changed`` / ``CustomOrder.clean``). Re-checking
        # it here against the client's *current* address list would break the
        # same "an order keeps moving after its address is unlinked" guarantee
        # those checks are gated to preserve -- a dispatch may happen long
        # after the client's saved addresses have since changed.

        if (
            source is not None
            and self.dispatch_details_id
            and source.dispatch_details_id != self.dispatch_details_id
        ):
            errors["dispatch_details"] = (
                "Dispatch details belong to a different order."
            )

        if errors:
            raise ValidationError(errors)
