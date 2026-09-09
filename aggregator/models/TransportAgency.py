from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class TransportAgency(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A transport agency, identified only by its name.

    A name is unique **per client**, not globally: two clients may each own
    their own row named "ABC Transport", but one client may not list that name
    twice. That is a cross-table rule, so it is enforced in
    ``aggregator/ClientOperations.py`` rather than by a database constraint.
    """

    name = models.CharField("name", max_length=255, db_index=True)

    class Meta:
        verbose_name = "transport agency"
        verbose_name_plural = "transport agencies"
        ordering = ["name"]

    def __str__(self):
        return self.name
