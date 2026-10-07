from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from common.models import (
    CreatedByModel,
    PrefixedPublicIdModel,
    SoftDeletedModel,
    TimeStampedModel,
    indian_now,
)

from .Status import StatusIds

ORDER_STATUS_CODES = {s.name for s in StatusIds.order_statuses()}
DISPATCH_REQUIRED_STATUS_CODES = {StatusIds.DISPATCHED.name, StatusIds.DELIVERED.name}
# Statuses in which an order holds stock: reserved (CONFIRMED) or consumed
# (DISPATCHED, DELIVERED). Such an order cannot be deleted -- see
# ``refuse_deleting_stock_holder``.
STOCK_HOLDING_STATUS_IDS = frozenset(
    {StatusIds.CONFIRMED, StatusIds.DISPATCHED, StatusIds.DELIVERED}
)


def refuse_deleting_stock_holder(order: models.Model) -> None:
    """Raise unless ``order`` (an Order or CustomOrder) may be soft-deleted.

    The stock math leaves deleted orders out entirely, which is only right if
    a deleted order never held stock: a CONFIRMED order's reservation would
    silently lapse, and a dispatched one's bags -- which physically left --
    would reappear as available stock and hand their raw and packing material
    back. So an order holding stock must first be moved out of it through its
    lifecycle (unverify / revert the dispatch / reject). A delivered order is
    history and can never be deleted.

    The stored status is read under a row lock, so a concurrent transition
    cannot slip between the check and the delete.
    """
    status_id = (
        type(order)._base_manager.select_for_update()
        .filter(pk=order.pk)
        .values_list("status_id", flat=True)
        .first()
    )
    if status_id in STOCK_HOLDING_STATUS_IDS:
        code = StatusIds(status_id).name
        raise ValidationError(
            f"Cannot delete an order that is {code}: it holds stock. "
            "Unverify, revert the dispatch of, or reject it first."
        )


def client_link_changed(instance: models.Model, *fields: str) -> bool:
    """Whether any of ``fields`` differs from what is stored for ``instance``.

    True for an unsaved instance. The address and agency an order was booked
    against are checked against the client's *live* links when they are set,
    not on every later save: the client's lists are full replacements that
    soft-delete a dropped link (and an address is keyed by its text, so fixing
    a typo unlinks the old one), and re-checking an unchanged reference would
    leave every open order using it unable to move again.
    """
    if instance._state.adding or instance.pk is None:
        return True
    stored = (
        type(instance)._base_manager.filter(pk=instance.pk).values(*fields).first()
    )
    if stored is None:
        return True
    return any(stored[field] != getattr(instance, field) for field in fields)


def default_expected_delivery_date():
    """Default expected delivery: the day after the order is booked."""
    return indian_now().date() + timedelta(days=1)


class Order(PrefixedPublicIdModel, TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A booked order for a client, made up of one or more ``OrderItem`` rows.

    Booked by a sales person (``created_by``). Dispatch details are attached
    later: at most one of ``dispatch_details`` / ``private_dispatch_details``
    may ever be set, and exactly one is required once the order is dispatched.

    ``transport_agency`` records *who* is meant to carry the order, chosen at
    booking time from the client's own agencies. It is optional: null means a
    private (own-vehicle) dispatch, which is the default assumption. It is
    independent of the dispatch details above, which are filled in afterwards
    with what actually happened.

    Exposed to the frontend by its ``public_id`` (``ORD-…``); the primary key is
    never sent out.
    """

    public_id_prefix = "ORD-"

    client = models.ForeignKey(
        "aggregator.Client",
        verbose_name="client",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    delivery_address = models.ForeignKey(
        "aggregator.Address",
        verbose_name="delivery address",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    status = models.ForeignKey(
        "aggregator.Status",
        verbose_name="status",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    expected_delivery_date = models.DateField(
        "expected delivery date",
        default=default_expected_delivery_date,
    )
    actual_delivery_date = models.DateField(
        "actual delivery date",
        null=True,
        blank=True,
    )
    dispatch_details = models.ForeignKey(
        "aggregator.DispatchDetails",
        verbose_name="dispatch details",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders",
    )
    private_dispatch_details = models.ForeignKey(
        "aggregator.PrivateDispatchDetails",
        verbose_name="private dispatch details",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders",
    )
    transport_agency = models.ForeignKey(
        "aggregator.TransportAgency",
        verbose_name="transport agency",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders",
        help_text=(
            "The client's transport agency carrying this order. Null means a "
            "private (own-vehicle) dispatch, which is the default."
        ),
    )
    booked_for = models.ForeignKey(
        "aggregator.ClientChildOrg",
        verbose_name="booked for",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders",
        help_text="The client's child org this order was booked on behalf of.",
    )
    special_comments = models.TextField("special comments", blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="verified by",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Sales admin who verified this order.",
    )
    verified_at = models.DateTimeField("verified at", null=True, blank=True)

    class Meta:
        verbose_name = "order"
        verbose_name_plural = "orders"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(
                    dispatch_details__isnull=False,
                    private_dispatch_details__isnull=False,
                ),
                name="ck_order_not_both_dispatch_details",
            ),
        ]

    def guard_soft_delete(self, perform):
        """See ``refuse_deleting_stock_holder``."""
        refuse_deleting_stock_holder(self)
        perform()

    def __str__(self):
        return self.public_id or "Order"

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

    @property
    def is_verified(self):
        return bool(self.status_id and self.status.code == StatusIds.CONFIRMED.name)

    @property
    def is_dispatched(self):
        return bool(self.status_id and self.status.code in DISPATCH_REQUIRED_STATUS_CODES)

    @property
    def active_dispatch(self):
        if self.dispatch_details_id:
            return self.dispatch_details
        if self.private_dispatch_details_id:
            return self.private_dispatch_details
        return None

    def clean(self):
        super().clean()
        errors = {}

        if self.status_id and self.status.code not in ORDER_STATUS_CODES:
            errors["status"] = "Invalid status for an order."

        if (
            self.status_id
            and self.status.code == StatusIds.CONFIRMED.name
            and (self.verified_by_id is None or self.verified_at is None)
        ):
            errors["status"] = "A verified order must record who verified it and when."

        if self.verified_by_id and not (
            self.verified_by.is_admin_user or self.verified_by.is_superuser
        ):
            errors["verified_by"] = "Orders can only be verified by a sales admin."

        if (
            self.client_id
            and self.delivery_address_id
            and client_link_changed(self, "client_id", "delivery_address_id")
        ):
            from .ClientAddress import ClientAddress

            belongs = ClientAddress.objects.filter(
                client_id=self.client_id,
                address_id=self.delivery_address_id,
            ).exists()
            if not belongs:
                errors["delivery_address"] = (
                    "Delivery address must belong to the selected client."
                )

        if (
            self.client_id
            and self.transport_agency_id
            and client_link_changed(self, "client_id", "transport_agency_id")
        ):
            from .ClientTransportAgency import ClientTransportAgency

            linked = ClientTransportAgency.objects.filter(
                client_id=self.client_id,
                transport_agency_id=self.transport_agency_id,
            ).exists()
            if not linked:
                errors["transport_agency"] = (
                    "Transport agency must belong to the selected client."
                )

        if (
            self.client_id
            and self.booked_for_id
            and self.booked_for.client_id != self.client_id
        ):
            errors["booked_for"] = "Booked-for child org belongs to a different client."

        if self.dispatch_details_id and self.private_dispatch_details_id:
            errors["dispatch_details"] = (
                "An order cannot have both dispatch details and private dispatch details."
            )

        if (
            self.status_id
            and self.status.code in DISPATCH_REQUIRED_STATUS_CODES
            and not self.dispatch_details_id
            and not self.private_dispatch_details_id
        ):
            errors["status"] = "Dispatch details are required once the order is dispatched."

        if self.created_by_id and not self.created_by.is_salesperson:
            errors["created_by"] = "Orders can only be created by a sales person."

        if self.client_id:
            if self.dispatch_details_id and self.dispatch_details.client_id != self.client_id:
                errors["dispatch_details"] = "Dispatch details belong to a different client."
            if (
                self.private_dispatch_details_id
                and self.private_dispatch_details.client_id != self.client_id
            ):
                errors["private_dispatch_details"] = (
                    "Dispatch details belong to a different client."
                )

        if errors:
            raise ValidationError(errors)
