from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class ClientTransportAgency(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """Links a ``Client`` to one of its ``TransportAgency`` rows."""

    client = models.ForeignKey(
        "aggregator.Client",
        verbose_name="client",
        on_delete=models.PROTECT,
        related_name="client_transport_agencies",
    )
    transport_agency = models.ForeignKey(
        "aggregator.TransportAgency",
        verbose_name="transport agency",
        on_delete=models.PROTECT,
        related_name="client_transport_agencies",
    )
    is_primary = models.BooleanField("is primary", default=False)

    class Meta:
        verbose_name = "client transport agency"
        verbose_name_plural = "client transport agencies"
        ordering = ["-is_primary", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["client", "transport_agency"],
                name="uniq_clienttransportagency_client_agency",
            ),
            models.UniqueConstraint(
                fields=["client"],
                condition=models.Q(is_primary=True, is_deleted=False),
                name="uniq_clienttransportagency_one_primary",
            ),
        ]

    def __str__(self):
        return (
            f"{self.client} → {self.transport_agency}"
            if self.client_id
            else "client transport agency"
        )
