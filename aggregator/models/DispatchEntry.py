from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from authentication.validators import validate_phone_number
from common.models import (
    PrefixedPublicIdModel,
    SoftDeletedModel,
    TimeStampedModel,
)


class DispatchEntry(PrefixedPublicIdModel, TimeStampedModel, SoftDeletedModel):
    """The challan record for one order: what left, to whom, on what.

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

    order = models.OneToOneField(
        "aggregator.Order",
        verbose_name="order",
        on_delete=models.PROTECT,
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
    vehicle_number = models.CharField("vehicle number", max_length=32)
    driver_name = models.CharField("driver name", max_length=255)
    driver_number = models.CharField(
        "driver number",
        max_length=10,
        validators=[validate_phone_number],
    )

    class Meta:
        verbose_name = "dispatch entry"
        verbose_name_plural = "dispatch entries"
        ordering = ["-dispatched_at", "-id"]

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
    def total_packets(self):
        return sum(
            (
                item.quantity * item.product_packaging.packets
                for item in self.items.all()
            ),
            0,
        )

    def clean(self):
        super().clean()
        errors = {}

        if self.order_id and self.client_id and self.order.client_id != self.client_id:
            errors["client"] = "A dispatch entry must name the order's own client."

        if self.client_id and self.client_address_id:
            from .ClientAddress import ClientAddress

            belongs = ClientAddress.objects.filter(
                client_id=self.client_id,
                address_id=self.client_address_id,
            ).exists()
            if not belongs:
                errors["client_address"] = (
                    "Client address must belong to the selected client."
                )

        if (
            self.order_id
            and self.dispatch_details_id
            and self.order.dispatch_details_id != self.dispatch_details_id
        ):
            errors["dispatch_details"] = (
                "Dispatch details belong to a different order."
            )

        if errors:
            raise ValidationError(errors)
