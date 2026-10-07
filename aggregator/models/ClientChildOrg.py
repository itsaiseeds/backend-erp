from django.db import models
from django.db.models.functions import Lower

from authentication.validators import validate_phone_number
from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class ClientChildOrg(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A downstream party a client books orders on behalf of ("booked for").

    Owned by one ``Client`` and unique on ``(client, party name, village)``,
    case-insensitively. Created only through order booking (get-or-create, see
    ``ClientChildOrgOperations.resolve_child_org``); never edited afterwards.
    Its address is informational: it is **not** the order's delivery address.

    Not exposed by a public id -- the integer ``id`` is what the pickers hand out.
    """

    client = models.ForeignKey(
        "aggregator.Client",
        verbose_name="client",
        on_delete=models.PROTECT,
        related_name="child_orgs",
    )
    party_name = models.CharField("party name", max_length=255)
    village_name = models.CharField("village name", max_length=255)
    address = models.ForeignKey(
        "aggregator.Address",
        verbose_name="address",
        on_delete=models.PROTECT,
        related_name="child_orgs",
    )
    transport_name = models.CharField("transport name", max_length=255, blank=True, default="")
    contact_number = models.CharField(
        "contact number",
        max_length=10,
        blank=True,
        null=True,
        validators=[validate_phone_number],
    )

    class Meta:
        verbose_name = "client child org"
        verbose_name_plural = "client child orgs"
        ordering = ["party_name", "village_name"]
        constraints = [
            models.UniqueConstraint(
                Lower("party_name"),
                Lower("village_name"),
                "client",
                condition=models.Q(is_deleted=False),
                name="uniq_clientchildorg_client_party_village",
            ),
        ]

    def __str__(self):
        return f"{self.party_name} ({self.village_name})"
