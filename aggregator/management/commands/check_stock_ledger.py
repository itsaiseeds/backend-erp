"""Compare the product stock ledger with the live stock figures.

Exits non-zero, listing each mismatch, when any product's ledger totals differ
from what the stock screens read.
"""

from django.core.management.base import BaseCommand, CommandError

from aggregator import StockLedgerOperations


class Command(BaseCommand):
    help = "Check that the stock ledger equals the live stock figures for every product."

    def handle(self, *args, **options):
        problems = StockLedgerOperations.check_ledger()
        if problems:
            for problem in problems:
                self.stderr.write(problem)
            raise CommandError(f"{len(problems)} stock ledger mismatch(es).")
        self.stdout.write(self.style.SUCCESS("The stock ledger matches the live figures."))
