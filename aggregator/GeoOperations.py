"""Bulk loading of Indian postal reference data: cities and their pincodes.

The Department of Posts publishes the *All India Pincode Directory*, one row per
post office. It is the only accurate source of the pincode -> city mapping this
app needs, and it is far too large to keep in ``sql/dml.sql``, so it is loaded
from a CSV on demand via ``manage.py load_geo_data``.

The directory is keyed on *district* and *taluk*, never on "city", so a taluk
becomes a :class:`~aggregator.models.City`. Rows whose taluk is a placeholder
(``NA`` and friends) fall back to their district, which is a city anyway
(Surat, Jaipur), so those pincodes are kept rather than dropped.

Two wrinkles the directory hands us, both handled here:

* Taluk names are **not** unique inside a state -- ``Kalol`` sits in three
  different Gujarat districts -- but ``City`` is unique on ``(state, name)``.
  A taluk that spans districts is therefore named ``"<taluk>, <district>"`` for
  *every* district it appears in. The suffix is applied consistently rather than
  only where needed to dodge a clash, so a user picking a city never has to
  guess which of two identically named rows is theirs.
* Spellings drift: ``Detroj- Rampura``, ``Detroj Rampura`` and
  ``Detroj-rampura`` are the same place. Names are matched case- and
  whitespace-insensitively, and the most frequent spelling of a name wins.

Loading is idempotent and re-runnable: existing cities and pincodes are
reused, soft-deleted ones are restored rather than duplicated, and nothing that
already exists is renumbered -- the baseline cities in ``sql/dml.sql`` keep
their ids, which many tests and ``Party`` rows depend on.
"""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from django.db import transaction

from aggregator.models import City, Country, Pincode, State

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from authentication.models import User

DEFAULT_STATE_NAMES = ("Gujarat", "Rajasthan")
INDIA_ISO_CODES = ("IN", "IND", "356")
STATE_CODES = {"Gujarat": "GJ", "Rajasthan": "RJ"}

REQUIRED_COLUMNS = ("pincode", "statename", "taluk")
DISTRICT_COLUMN = "districtname"

#: Bulk-insert chunk. Sized so a full state's pincodes go in a handful of round
#: trips without holding one statement open long enough to trip a lock timeout.
BATCH_SIZE = 1000

_PLACEHOLDER_NAMES = {"", "-", "--", "NA", "NIL", "NONE", "UNKNOWN"}
_WHITESPACE = re.compile(r"\s+")
_SPACE_AROUND_HYPHEN = re.compile(r"\s*-\s*")


@dataclass(frozen=True)
class PostalRecord:
    """One directory row: a pincode and where the office serving it sits."""

    state: str
    taluk: str
    district: str
    pincode: str


@dataclass
class GeoLoadPlan:
    """What a directory file resolves to, before anything is written."""

    cities: list[tuple[str, str]] = field(default_factory=list)
    pincodes: list[tuple[str, str, str]] = field(default_factory=list)
    rows_read: int = 0
    rows_ignored: int = 0
    rows_missing_taluk: int = 0
    pincodes_in_several_cities: int = 0
    ambiguous_taluks: list[str] = field(default_factory=list)


def _clean(value: str | None) -> str:
    """Trim and collapse internal whitespace."""
    return _WHITESPACE.sub(" ", value or "").strip()


def _clean_place(value: str | None) -> str:
    """Clean a taluk / district name, or return ``""`` for a placeholder.

    ``NA``, ``N.A.``, ``NIL`` and blanks all mean "the directory did not say",
    which is different from a place genuinely called ``-``.
    """
    text = _SPACE_AROUND_HYPHEN.sub("-", _clean(value))
    return "" if text.upper().strip(".") in _PLACEHOLDER_NAMES else text


def _canonical_spelling(variants: Counter[str]) -> str:
    """Pick one spelling for the case/whitespace variants of a single name.

    Most frequent wins, alphabetically first on a tie, so the choice is stable
    across runs and the file can be re-loaded without churning names.
    """
    return min(variants, key=lambda name: (-variants[name], name))


def resolve_actor(phone_number: str | None = None) -> User | None:
    """The user to record as ``created_by`` on the loaded rows.

    ``created_by`` is nullable in the database but the admin lists it, and
    ``sql/dml.sql`` attributes its baseline geography to user 1, so a load with
    no actor leaves an audit gap. Falls back to the first superuser.
    """
    from django.contrib.auth import get_user_model

    users = get_user_model()
    if phone_number:
        return users.objects.filter(phone_number=phone_number).first()
    return users.objects.filter(is_superuser=True).order_by("id").first()


def read_pincode_directory(
    csv_path: str | Path,
    state_names: Iterable[str] = DEFAULT_STATE_NAMES,
) -> GeoLoadPlan:
    """Turn an All India Pincode Directory CSV into cities and pincodes.

    Column names are matched case-insensitively, so both the Department of Posts
    export (``statename``, ``districtname``) and the community mirrors that keep
    camelCase (``stateName``, ``districtName``) load unchanged. Rows for states
    that were not asked for are skipped without being counted as errors.
    """
    wanted = {_clean(name).casefold(): _clean(name) for name in state_names}
    records: list[PostalRecord] = []
    plan = GeoLoadPlan()

    path = Path(csv_path)
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        reader = csv.reader(handle)
        try:
            header = [_clean(column).casefold() for column in next(reader)]
        except StopIteration:
            raise ValueError(f"{path} is empty.") from None

        missing = [column for column in REQUIRED_COLUMNS if column not in header]
        if missing:
            raise ValueError(f"{path} has no {', '.join(missing)} column(s).")
        column = {name: header.index(name) for name in header}

        for row in reader:
            plan.rows_read += 1
            if len(row) < len(header):
                plan.rows_ignored += 1
                continue

            state = _clean(row[column["statename"]])
            if state.casefold() not in wanted:
                continue
            state = wanted[state.casefold()]

            pincode = _clean(row[column["pincode"]])
            if not (pincode.isdigit() and len(pincode) == 6):
                plan.rows_ignored += 1
                continue

            taluk = _clean_place(row[column["taluk"]])
            district = ""
            if DISTRICT_COLUMN in column:
                district = _clean_place(row[column[DISTRICT_COLUMN]])
            if not taluk:
                # No taluk on the row, but the district is a city in its own
                # right, so keep the pincode under that instead of losing it.
                plan.rows_missing_taluk += 1
                taluk = district
            if not taluk:
                plan.rows_ignored += 1
                continue

            records.append(
                PostalRecord(state=state, taluk=taluk, district=district, pincode=pincode)
            )

    if not records:
        raise ValueError(
            f"{path} holds no rows for {', '.join(sorted(set(wanted.values())))}."
        )

    plan.cities, plan.pincodes, plan.ambiguous_taluks, plan.pincodes_in_several_cities = (
        _resolve_place_names(records)
    )
    return plan


def _resolve_place_names(
    records: list[PostalRecord],
) -> tuple[list[tuple[str, str]], list[tuple[str, str, str]], list[str], int]:
    """Fold taluk spellings and district clashes into one city name per row.

    Returns the distinct ``(state, city)`` pairs, the distinct
    ``(state, city, pincode)`` triples, the taluks that needed a district
    suffix, and how many pincodes ended up under more than one city.
    """
    spellings: dict[str, Counter[str]] = defaultdict(Counter)
    districts: dict[str, set[str]] = defaultdict(set)
    for record in records:
        key = record.taluk.casefold()
        spellings[key][record.taluk] += 1
        districts[key].add(record.district)

    def city_name(key: str, district: str) -> str:
        label = _canonical_spelling(spellings[key])
        if len(districts[key]) > 1 and district:
            return f"{label}, {district}"
        return label

    cities: set[tuple[str, str]] = set()
    pincodes: set[tuple[str, str, str]] = set()
    pincode_cities: dict[str, set[str]] = defaultdict(set)
    for record in records:
        name = city_name(record.taluk.casefold(), record.district)
        cities.add((record.state, name))
        pincodes.add((record.state, name, record.pincode))
        pincode_cities[record.pincode].add(name)

    ambiguous = sorted(
        _canonical_spelling(spellings[key])
        for key, found in districts.items()
        if len(found) > 1
    )
    shared = sum(1 for cities_for in pincode_cities.values() if len(cities_for) > 1)
    return sorted(cities), sorted(pincodes), ambiguous, shared


def _india() -> Country:
    """The one country this loader will touch.

    ``Country`` is unique on both name and iso code, and the app resolves India
    by any of three spellings already (``CitiesView`` and the Android twin), so
    the same lookup is used here.
    """
    country = Country.all_objects.filter(name__iexact="India").first()
    if country is None:
        country = Country.all_objects.filter(iso_code__in=INDIA_ISO_CODES).first()
    if country is None:
        raise ValueError("No India country row exists; create it before loading geography.")
    return country


def _load_states(
    plan: GeoLoadPlan, country: Country, actor: User | None, dry_run: bool
) -> dict[str, State]:
    """Map each planned state name onto a ``State`` row, creating it if absent."""
    states: dict[str, State] = {}
    for state_name in sorted({state for state, _ in plan.cities}):
        existing = State.all_objects.filter(country=country, name__iexact=state_name).first()
        if existing is not None:
            if existing.is_deleted:
                existing.restore()
            states[state_name] = existing
            continue
        state = State(
            name=state_name,
            code=STATE_CODES.get(state_name),
            country=country,
            created_by=actor,
        )
        if not dry_run:
            state.save()
        states[state_name] = state
    return states


def _existing_cities(states: dict[str, State]) -> dict[str, dict[str, City]]:
    """Case-folded name -> city, for every city already in each state."""
    return {
        state_name: {
            _clean(city.name).casefold(): city for city in City.all_objects.filter(state=state)
        }
        for state_name, state in states.items()
    }


def load_geo_data(
    plan: GeoLoadPlan,
    actor: User | None = None,
    dry_run: bool = False,
) -> dict[str, int | bool]:
    """Write a :class:`GeoLoadPlan` to the database and report what happened.

    Safe to run repeatedly: cities and pincodes that already exist are counted
    and left alone, and a soft-deleted one is restored instead of being created
    a second time. ``dry_run`` performs every lookup but no writes, so it can
    report what a real run would create.
    """
    summary: dict[str, int | bool] = {
        "dry_run": dry_run,
        "cities_created": 0,
        "cities_reused": 0,
        "cities_restored": 0,
        "pincodes_created": 0,
        "pincodes_reused": 0,
        "pincodes_restored": 0,
    }

    with transaction.atomic():
        country = _india()
        states = _load_states(plan, country, actor, dry_run)
        buckets = _existing_cities(states)

        pending: list[City] = []
        for state_name, city_name in plan.cities:
            state = states[state_name]
            key = _clean(city_name).casefold()
            city = buckets[state_name].get(key)
            if city is None:
                city = City(name=city_name, state=state, created_by=actor)
                buckets[state_name][key] = city
                pending.append(city)
                summary["cities_created"] += 1
            elif city.is_deleted:
                summary["cities_restored"] += 1
                if not dry_run:
                    city.restore()
            else:
                summary["cities_reused"] += 1

        if pending and not dry_run:
            City.all_objects.bulk_create(pending, batch_size=BATCH_SIZE)

        # One query for every pincode already attached to a city we touched,
        # rather than one per (city, code) pair.
        stored: dict[int, dict[str, Pincode]] = defaultdict(dict)
        city_ids = [
            city.pk
            for bucket in buckets.values()
            for city in bucket.values()
            if city.pk is not None
        ]
        if city_ids:
            for stored_row in Pincode.all_objects.filter(city_id__in=city_ids).only(
                "city_id", "code", "is_deleted"
            ):
                stored[stored_row.city_id][_clean(stored_row.code)] = stored_row

        new_pincodes: list[Pincode] = []
        for state_name, city_name, pincode in plan.pincodes:
            city = buckets[state_name][_clean(city_name).casefold()]
            existing = stored.get(city.pk, {}).get(pincode) if city.pk is not None else None
            if existing is None:
                new_pincodes.append(Pincode(code=pincode, city=city, created_by=actor))
                summary["pincodes_created"] += 1
            elif existing.is_deleted:
                summary["pincodes_restored"] += 1
                if not dry_run:
                    existing.restore()
            else:
                summary["pincodes_reused"] += 1

        if new_pincodes and not dry_run:
            Pincode.all_objects.bulk_create(new_pincodes, batch_size=BATCH_SIZE)

    return summary


def describe_plan(plan: GeoLoadPlan) -> Iterator[str]:
    """Human-readable lines describing a plan, for the command's stdout."""
    yield (
        f"Read {plan.rows_read} rows "
        f"({plan.rows_ignored} ignored, {plan.rows_missing_taluk} with no taluk)."
    )
    for state_name in sorted({state for state, _ in plan.cities}):
        cities = sum(1 for state, _ in plan.cities if state == state_name)
        pincodes = sum(1 for state, _, _ in plan.pincodes if state == state_name)
        yield f"  {state_name}: {cities} cities, {pincodes} pincodes."
    if plan.ambiguous_taluks:
        yield (
            f"{len(plan.ambiguous_taluks)} taluk name(s) span more than one district "
            f"and were suffixed with their district: {', '.join(plan.ambiguous_taluks[:10])}"
            + (" ..." if len(plan.ambiguous_taluks) > 10 else "")
        )
    if plan.pincodes_in_several_cities:
        yield (
            f"{plan.pincodes_in_several_cities} pincode(s) serve more than one taluk and "
            "are stored under each, matching how the directory reports them."
        )
