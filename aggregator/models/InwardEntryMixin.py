from django.core.exceptions import ValidationError
from django.db import models


class InwardEntryMixin(models.Model):
    """Shared fields for inward stock-entry records (raw and other material).

    There is no explicit ``entry_date`` column: the entry's date is
    ``created_at`` from ``TimeStampedModel``.

    ``effective_date`` is the day the entry starts counting toward stock. For
    other material it is stamped at booking (today); for raw material it is
    stamped by the ``Lab Testing -> In Use`` flip, and reverting a raw lot
    clears the date again. A row counts toward stock only once that date has
    come.

    ``party`` is required unless ``return_order`` is set: an accepted return
    books its rows with no party, since the goods came from a client.
    """

    effective_date = models.DateField(
        "effective date",
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "The day the row starts counting toward stock: stamped at booking "
            "for other material, at the 'in use' flip for raw material."
        ),
    )
    party = models.ForeignKey(
        "aggregator.Party",
        verbose_name="party",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Null only for stock a ReturnOrder booked back in.",
    )
    return_order = models.ForeignKey(
        "aggregator.ReturnOrder",
        verbose_name="return order",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        db_index=True,
        help_text=(
            "The accepted return this row came from. Such a row cannot be edited "
            "or deleted directly: only reverting the accept removes it."
        ),
    )

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if self.party_id is None and self.return_order_id is None:
            raise ValidationError({"party": "A party is required."})

    def refuse_return_lot_change(self) -> None:
        """Raise unless this row may be edited or deleted directly.

        A row an accepted return booked is owned by that return: only
        ``ReturnOrderOperations.revert_accept_return_order`` removes it.
        """
        ret = self.return_order
        if ret is not None:
            raise ValidationError(
                f"This lot came from return {ret.public_id}; "
                "revert the accept of that return instead."
            )
