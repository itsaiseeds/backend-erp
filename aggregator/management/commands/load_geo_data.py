"""Load cities and pincodes for a set of states from an All India Pincode CSV.

The Department of Posts directory is far too large to keep in ``sql/dml.sql``,
so it is supplied at run time. Point this at the Gujarat / Rajasthan rows of
the *All India Pincode Directory* (data.gov.in, Government Open Data License -
India) or any mirror with the same columns::

    manage.py load_geo_data --csv ~/Downloads/all_india_pincode.csv
    manage.py load_geo_data --csv pincodes.csv --state Gujarat --dry-run

Re-running is safe: existing cities and pincodes are left alone, and
soft-deleted ones are restored rather than duplicated.
"""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from aggregator import GeoOperations


class Command(BaseCommand):
    help = "Load cities and pincodes for the given states from an India pincode directory CSV."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            required=True,
            type=Path,
            help="Path to the All India Pincode Directory CSV.",
        )
        parser.add_argument(
            "--state",
            action="append",
            dest="states",
            metavar="NAME",
            help=(
                "State to load; repeat for more. Defaults to "
                f"{' and '.join(GeoOperations.DEFAULT_STATE_NAMES)}."
            ),
        )
        parser.add_argument(
            "--actor",
            metavar="PHONE",
            help=(
                "Phone number of the user recorded as created_by. "
                "Defaults to the first superuser."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be loaded without writing anything.",
        )

    def handle(self, *args, **options):
        states = tuple(options["states"] or GeoOperations.DEFAULT_STATE_NAMES)
        try:
            plan = GeoOperations.read_pincode_directory(options["csv"], states)
            actor = GeoOperations.resolve_actor(options["actor"])
            summary = GeoOperations.load_geo_data(plan, actor=actor, dry_run=options["dry_run"])
        except ValueError as exc:
            raise CommandError(str(exc)) from None

        for line in GeoOperations.describe_plan(plan):
            self.stdout.write(line)

        if not actor:
            self.stdout.write(
                self.style.WARNING(
                    "No actor found, so created_by will be empty on the new rows."
                )
            )

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run, nothing written. Would create {summary['cities_created']} "
                    f"city/cities and {summary['pincodes_created']} pincode(s)."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Cities: {summary['cities_created']} created, "
                f"{summary['cities_reused']} already present, "
                f"{summary['cities_restored']} restored. "
                f"Pincodes: {summary['pincodes_created']} created, "
                f"{summary['pincodes_reused']} already present, "
                f"{summary['pincodes_restored']} restored."
            )
        )
