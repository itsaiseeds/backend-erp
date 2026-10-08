"""Re-key the packing-material ledger lines per configuration (run once after deploy).

See ``docs/prd/other-material-per-configuration-stock.md``. Idempotent.
"""

from django.core.management.base import BaseCommand

from aggregator import StockLedgerOperations


class Command(BaseCommand):
    help = "Rebuild OTHER stock ledger lines per (product, packet weight, material type)."

    def handle(self, *args, **options):
        count = StockLedgerOperations.rebuild_other_material_ledger()
        self.stdout.write(
            self.style.SUCCESS(f"Wrote {count} packing-material ledger lines.")
        )
