"""Go-live seed for the product stock ledger (run once).

Writes a ``LEDGER_START`` event per product and the recipe layers of every
existing latest count row. No live figure moves. Refuses to run a second time.
"""

from django.core.management.base import BaseCommand, CommandError

from aggregator import StockLedgerOperations


class Command(BaseCommand):
    help = "Seed the product stock ledger from the live stock position (once)."

    def handle(self, *args, **options):
        try:
            count = StockLedgerOperations.seed_ledger()
        except ValueError as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(self.style.SUCCESS(f"Seeded the stock ledger for {count} products."))
