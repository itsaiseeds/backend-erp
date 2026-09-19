from django.db import models


class InwardEntryMixin(models.Model):
    """Shared fields for inward stock-entry records (raw and other material).

    There is no explicit ``entry_date`` column: the entry's date is
    ``created_at`` from ``TimeStampedModel``.

    ``effective_date`` is the day the entry starts counting toward stock. For
    other material it is stamped at booking (today); for raw material it is
    stamped by the ``lab_testing -> in_use`` flip, and reverting a raw lot
    clears the date again. A row counts toward stock only once that date has
    come.
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
        related_name="+",
    )

    class Meta:
        abstract = True
