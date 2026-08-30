"""Seed India states + cities into the ``aggregator`` geography tables.

Idempotent: resolves the India ``Country`` and each ``State`` by name, then
``get_or_create``s every city under its state. Endpoint-backed by
``/api/utilities/cities``.

Source: ``data/india_cities.csv`` (``state, city``; 4,242 rows across all 36
states/UTs) from the MIT-licensed ``io-PEAK/india-edu-cities-data`` package.
"""

import csv
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from aggregator.models import City, Country, State

DATA_FILE = Path(__file__).resolve().parents[3] / "data" / "india_cities.csv"


class Command(BaseCommand):
    help = "Load India states and cities into aggregator from data/india_cities.csv"

    def handle(self, *args, **options):
        User = get_user_model()
        actor = User.objects.filter(is_superuser=True).first()

        india, _ = Country.objects.update_or_create(
            iso_code="IN",
            defaults={"name": "India", "created_by": actor},
        )

        with DATA_FILE.open(newline="") as fh:
            rows = list(csv.DictReader(fh))

        states: dict[str, State] = {}
        states_created = 0
        cities_created = 0
        for row in rows:
            state_name = (row.get("state") or "").strip()
            city_name = (row.get("city") or "").strip()
            if not state_name or not city_name:
                continue
            if state_name not in states:
                state, created = State.objects.get_or_create(
                    country=india,
                    name=state_name,
                    defaults={"created_by": actor},
                )
                states[state_name] = state
                states_created += int(created)
            _, created = City.objects.get_or_create(
                state=states[state_name],
                name=city_name,
                defaults={"created_by": actor},
            )
            cities_created += int(created)

        message = (
            f"Loaded India geography from {DATA_FILE}: {states_created} states, "
            f"{cities_created} cities created ({len(rows)} source rows)."
        )
        self.stdout.write(self.style.SUCCESS(message))
