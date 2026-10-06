"""Tests for the pincode-directory loader behind ``manage.py load_geo_data``.

The directory itself is a Department of Posts export far too large to keep in
the repo, so these drive it from a small hand-written CSV carrying the quirks
the real file is full of: taluk names that repeat across districts, spellings
that differ only by case, ``NA`` in place of a taluk, a pincode serving two
taluks, and rows for other states.

``sql/dml.sql`` already holds India / Gujarat / Surat with pincode ``395003``,
and a load must not disturb it, so the fixture includes that exact row and the
tests assert the baseline ids survive.
"""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError

from aggregator import GeoOperations
from aggregator.models import City, Pincode, State
from tests.common import DMLTestCase

HEADER = [
    "officename",
    "pincode",
    "officetype",
    "deliverystatus",
    "divisionname",
    "regionname",
    "circlename",
    "taluk",
    "districtname",
    "statename",
]

# (office, pincode, taluk, district, state)
ROWS = [
    # Gujarat: Surat is the dml.sql baseline and must be reused, not duplicated.
    ("Surat H.O", "395003", "Surat", "Surat", "GUJARAT"),
    ("Patan S.O", "384221", "Patan", "Patan", "GUJARAT"),
    # The same taluk name in a second district -- needs the district suffix.
    ("Patan B.O", "384241", "Patan", "Mahesana", "GUJARAT"),
    # One place, three spellings: spaces and case must collapse.
    ("Kadi S.O", "382230", "Kadi", "Ahmedabad", "GUJARAT"),
    ("Kadi2 S.O", "382231", "kadi", "Ahmedabad", "GUJARAT"),
    ("Kadi3 S.O", "382232", "Kadi", "Ahmedabad", "GUJARAT"),
    # No taluk on the row: the district is a city in its own right.
    ("Ambavadi S.O", "380001", "NA", "Ahmedabad", "GUJARAT"),
    # One pincode serving two taluks, which the directory reports.
    ("Shared S.O", "384245", "Unjha", "Patan", "GUJARAT"),
    ("Shared2 S.O", "384245", "Visnagar", "Mehsana", "GUJARAT"),
    # Not a pincode at all, so ignored rather than stored.
    ("Broken S.O", "38001", "Unjha", "Patan", "GUJARAT"),
    # Rajasthan.
    ("Jaipur H.O", "302001", "Jaipur", "Jaipur", "RAJASTHAN"),
    ("Badli S.O", "303001", "Badli", "Jaipur", "RAJASTHAN"),
    # Another state entirely -- must never be loaded.
    ("Pune H.O", "411001", "Pune", "Pune", "MAHARASHTRA"),
]


def write_directory(testcase: DMLTestCase, rows=ROWS, header=None) -> Path:
    """Write a directory-shaped CSV to a temp file and clean it up with the test."""
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".csv", newline="", delete=False, encoding="utf-8"
    )
    with handle:
        writer = csv.writer(handle)
        writer.writerow(header or HEADER)
        for office, pincode, taluk, district, state in rows:
            writer.writerow(
                [
                    office,
                    pincode,
                    "B.O",
                    "Delivery",
                    district,
                    district,
                    state,
                    taluk,
                    district,
                    state,
                ]
            )
    path = Path(handle.name)
    testcase.addCleanup(path.unlink, True)
    return path


def city_names(plan: GeoOperations.GeoLoadPlan, state_name: str) -> list[str]:
    return [name for state, name in plan.cities if state == state_name]


def pincodes_for(plan: GeoOperations.GeoLoadPlan, city_name: str) -> list[str]:
    return sorted(pincode for _, name, pincode in plan.pincodes if name == city_name)


class PincodeDirectoryParsingTest(DMLTestCase):
    """Parsing a directory CSV into cities and pincodes, before any DB writes.

    Run: tests/test_load_geo_data.py::PincodeDirectoryParsingTest
    """

    def setUp(self):
        super().setUp()
        self.csv_path = write_directory(self)

    def test_taluk_becomes_a_city(self):
        """Run: tests/test_load_geo_data.py::PincodeDirectoryParsingTest::test_taluk_becomes_a_city"""
        plan = GeoOperations.read_pincode_directory(self.csv_path, ["Gujarat"])
        names = city_names(plan, "Gujarat")
        self.assertIn("Kadi", names)
        self.assertIn("Unjha", names)
        self.assertNotIn("Badli", names, "Badli is in Rajasthan, which was not requested")
        self.assertEqual(pincodes_for(plan, "Unjha"), ["384245"])

    def test_only_requested_states_are_kept(self):
        """Run: tests/test_load_geo_data.py::PincodeDirectoryParsingTest::test_only_requested_states_are_kept"""
        plan = GeoOperations.read_pincode_directory(self.csv_path, ["Rajasthan"])
        self.assertEqual({state for state, _ in plan.cities}, {"Rajasthan"})
        self.assertEqual(city_names(plan, "Rajasthan"), ["Badli", "Jaipur"])

    def test_taluk_in_two_districts_is_suffixed_consistently(self):
        """Run: tests/test_load_geo_data.py::PincodeDirectoryParsingTest::test_taluk_in_two_districts_is_suffixed_consistently"""
        plan = GeoOperations.read_pincode_directory(self.csv_path, ["Gujarat"])
        names = city_names(plan, "Gujarat")
        # Both instances carry the suffix, so nothing depends on which district
        # the parser happened to see first.
        self.assertIn("Patan, Patan", names)
        self.assertIn("Patan, Mahesana", names)
        self.assertNotIn("Patan", names)
        self.assertIn("Patan", plan.ambiguous_taluks)

    def test_spelling_variants_collapse_to_one_city(self):
        """Run: tests/test_load_geo_data.py::PincodeDirectoryParsingTest::test_spelling_variants_collapse_to_one_city"""
        plan = GeoOperations.read_pincode_directory(self.csv_path, ["Gujarat"])
        self.assertEqual(pincodes_for(plan, "Kadi"), ["382230", "382231", "382232"])
        self.assertEqual(city_names(plan, "Gujarat").count("Kadi"), 1)

    def test_row_without_a_taluk_falls_back_to_its_district(self):
        """Run: tests/test_load_geo_data.py::PincodeDirectoryParsingTest::test_row_without_a_taluk_falls_back_to_its_district"""
        plan = GeoOperations.read_pincode_directory(self.csv_path, ["Gujarat"])
        self.assertEqual(pincodes_for(plan, "Ahmedabad"), ["380001"])
        self.assertEqual(plan.rows_missing_taluk, 1)

    def test_ragged_pincode_is_ignored(self):
        """Run: tests/test_load_geo_data.py::PincodeDirectoryParsingTest::test_ragged_pincode_is_ignored"""
        plan = GeoOperations.read_pincode_directory(self.csv_path, ["Gujarat"])
        stored = {pincode for _, _, pincode in plan.pincodes}
        self.assertNotIn("38001", stored)
        self.assertEqual(plan.rows_ignored, 1)

    def test_pincode_under_two_cities_is_planned_for_each(self):
        """A code is unique per city, so each taluk it serves gets its own row.

        Run: tests/test_load_geo_data.py::PincodeDirectoryParsingTest::test_pincode_under_two_cities_is_planned_for_each
        """
        plan = GeoOperations.read_pincode_directory(self.csv_path, ["Gujarat"])
        serving = sorted(name for _, name, pincode in plan.pincodes if pincode == "384245")
        self.assertEqual(len(serving), 2)
        self.assertIn("Unjha", serving)
        self.assertEqual(plan.pincodes_in_several_cities, 1)

    def test_camel_case_headers_are_accepted(self):
        """Run: tests/test_load_geo_data.py::PincodeDirectoryParsingTest::test_camel_case_headers_are_accepted"""
        camel = [
            "officeName",
            "pincode",
            "officeType",
            "deliveryStatus",
            "divisionName",
            "regionName",
            "circleName",
            "taluk",
            "districtName",
            "stateName",
        ]
        plan = GeoOperations.read_pincode_directory(write_directory(self, header=camel), ["Gujarat"])
        self.assertIn("Kadi", city_names(plan, "Gujarat"))

    def test_missing_column_is_rejected(self):
        """Run: tests/test_load_geo_data.py::PincodeDirectoryParsingTest::test_missing_column_is_rejected"""
        path = write_directory(self, header=[c for c in HEADER if c != "taluk"])
        with self.assertRaisesMessage(ValueError, "taluk"):
            GeoOperations.read_pincode_directory(path, ["Gujarat"])

    def test_no_matching_state_is_rejected(self):
        """Run: tests/test_load_geo_data.py::PincodeDirectoryParsingTest::test_no_matching_state_is_rejected"""
        with self.assertRaisesMessage(ValueError, "Kerala"):
            GeoOperations.read_pincode_directory(self.csv_path, ["Kerala"])


class LoadGeoDataTest(DMLTestCase):
    """Writing a plan to the database, and re-running it safely.

    Run: tests/test_load_geo_data.py::LoadGeoDataTest
    """

    def setUp(self):
        super().setUp()
        self.csv_path = write_directory(self)
        self.plan = GeoOperations.read_pincode_directory(self.csv_path, ["Gujarat", "Rajasthan"])
        self.actor = GeoOperations.resolve_actor()

    def test_cities_and_pincodes_are_created(self):
        """Run: tests/test_load_geo_data.py::LoadGeoDataTest::test_cities_and_pincodes_are_created"""
        summary = GeoOperations.load_geo_data(self.plan, actor=self.actor)

        kadi = City.all_objects.get(state__name="Gujarat", name="Kadi")
        self.assertEqual(
            sorted(Pincode.all_objects.filter(city=kadi).values_list("code", flat=True)),
            ["382230", "382231", "382232"],
        )
        # The dml.sql pincode rows live inside the DUMMY DATA fence, so the test
        # database starts with no pincodes at all and every planned one is new.
        self.assertEqual(summary["pincodes_created"], len(self.plan.pincodes))
        # Surat, Ahmedabad and Jaipur are city rows in dml.sql that sit outside
        # the DUMMY DATA fence, so they are reused; Ahmedabad is reused twice
        # over, because the taluk-less row falls back to it as a district.
        self.assertEqual(summary["cities_reused"], 3)
        self.assertEqual(summary["cities_created"], len(self.plan.cities) - 3)

    def test_a_pincode_serving_two_cities_is_stored_per_city(self):
        """The two taluks the directory gives a code each get their own row.

        Run: tests/test_load_geo_data.py::LoadGeoDataTest::test_a_pincode_serving_two_cities_is_stored_per_city
        """
        GeoOperations.load_geo_data(self.plan, actor=self.actor)

        rows = Pincode.all_objects.filter(code="384245")
        self.assertEqual(rows.count(), 2)
        self.assertEqual(rows.values("city_id").distinct().count(), 2)

    def test_baseline_city_is_reused_not_duplicated(self):
        """Run: tests/test_load_geo_data.py::LoadGeoDataTest::test_baseline_city_is_reused_not_duplicated"""
        baseline_city = City.objects.get(name="Surat", state__name="Gujarat")
        baseline_id = baseline_city.id

        GeoOperations.load_geo_data(self.plan, actor=self.actor)

        self.assertEqual(City.all_objects.filter(name="Surat").count(), 1)
        self.assertEqual(
            City.objects.get(name="Surat", state__name="Gujarat").id,
            baseline_id,
            "the dml.sql city was recreated instead of reused, so its id moved",
        )
        # The new pincode hangs off the existing city rather than a copy of it.
        self.assertEqual(Pincode.all_objects.get(code="395003").city_id, baseline_id)

    def test_second_run_creates_nothing(self):
        """Run: tests/test_load_geo_data.py::LoadGeoDataTest::test_second_run_creates_nothing"""
        GeoOperations.load_geo_data(self.plan, actor=self.actor)
        cities_before = City.all_objects.count()
        pincodes_before = Pincode.all_objects.count()

        summary = GeoOperations.load_geo_data(self.plan, actor=self.actor)

        self.assertEqual(summary["cities_created"], 0)
        self.assertEqual(summary["pincodes_created"], 0)
        self.assertEqual(summary["cities_reused"], len(self.plan.cities))
        self.assertEqual(summary["pincodes_reused"], len(self.plan.pincodes))
        self.assertEqual(City.all_objects.count(), cities_before)
        self.assertEqual(Pincode.all_objects.count(), pincodes_before)

    def test_soft_deleted_rows_are_restored(self):
        """Run: tests/test_load_geo_data.py::LoadGeoDataTest::test_soft_deleted_rows_are_restored"""
        GeoOperations.load_geo_data(self.plan, actor=self.actor)
        City.all_objects.get(state__name="Gujarat", name="Kadi").mark_deleted(self.actor)

        summary = GeoOperations.load_geo_data(self.plan, actor=self.actor)

        self.assertEqual(summary["cities_restored"], 1)
        self.assertEqual(summary["cities_created"], 0)
        self.assertEqual(City.all_objects.filter(state__name="Gujarat", name="Kadi").count(), 1)
        self.assertTrue(City.objects.filter(state__name="Gujarat", name="Kadi").exists())

    def test_soft_deleted_pincode_is_restored(self):
        """Run: tests/test_load_geo_data.py::LoadGeoDataTest::test_soft_deleted_pincode_is_restored"""
        GeoOperations.load_geo_data(self.plan, actor=self.actor)
        kadi = City.objects.get(state__name="Gujarat", name="Kadi")
        pincode_id = Pincode.objects.get(city=kadi, code="382230").id
        Pincode.all_objects.get(pk=pincode_id).mark_deleted(self.actor)

        summary = GeoOperations.load_geo_data(self.plan, actor=self.actor)

        self.assertEqual(summary["pincodes_restored"], 1)
        self.assertEqual(summary["pincodes_created"], 0)
        self.assertEqual(Pincode.all_objects.filter(pk=pincode_id).count(), 1)
        restored = Pincode.objects.get(city=kadi, code="382230")
        self.assertEqual(restored.id, pincode_id)

    def test_dry_run_writes_nothing(self):
        """Run: tests/test_load_geo_data.py::LoadGeoDataTest::test_dry_run_writes_nothing"""
        cities_before = City.all_objects.count()
        pincodes_before = Pincode.all_objects.count()

        summary = GeoOperations.load_geo_data(self.plan, actor=self.actor, dry_run=True)

        self.assertTrue(summary["dry_run"])
        self.assertGreater(summary["cities_created"], 0)
        self.assertEqual(City.all_objects.count(), cities_before)
        self.assertEqual(Pincode.all_objects.count(), pincodes_before)

    def test_missing_state_is_created_under_india(self):
        """Run: tests/test_load_geo_data.py::LoadGeoDataTest::test_missing_state_is_created_under_india"""
        plan = GeoOperations.read_pincode_directory(self.csv_path, ["Maharashtra"])
        self.assertFalse(State.objects.filter(name="Maharashtra").exists())

        summary = GeoOperations.load_geo_data(plan, actor=self.actor)

        self.assertEqual(summary["cities_created"], 1)
        state = State.objects.get(name="Maharashtra")
        self.assertEqual(state.country.name, "India")
        self.assertIsNone(state.code, "an unknown state has no abbreviation to guess at")

    def test_rows_record_the_actor(self):
        """Run: tests/test_load_geo_data.py::LoadGeoDataTest::test_rows_record_the_actor"""
        GeoOperations.load_geo_data(self.plan, actor=self.actor)
        kadi = City.all_objects.get(state__name="Gujarat", name="Kadi")
        self.assertEqual(kadi.created_by_id, self.actor.id)
        self.assertEqual(kadi.created_by.phone_number, "9999999999")


class LoadGeoDataCommandTest(DMLTestCase):
    """The ``load_geo_data`` management command wrapping the loader.

    Run: tests/test_load_geo_data.py::LoadGeoDataCommandTest
    """

    def setUp(self):
        super().setUp()
        self.csv_path = str(write_directory(self))

    def test_command_loads_both_default_states(self):
        """Run: tests/test_load_geo_data.py::LoadGeoDataCommandTest::test_command_loads_both_default_states"""
        call_command("load_geo_data", csv=self.csv_path)

        self.assertTrue(City.objects.filter(state__name="Gujarat", name="Kadi").exists())
        self.assertTrue(City.objects.filter(state__name="Rajasthan", name="Badli").exists())
        self.assertFalse(City.objects.filter(name="Pune").exists(), "Maharashtra was not requested")

    def test_command_honours_a_single_state(self):
        """Run: tests/test_load_geo_data.py::LoadGeoDataCommandTest::test_command_honours_a_single_state"""
        call_command("load_geo_data", csv=self.csv_path, states=["Gujarat"])

        self.assertTrue(City.objects.filter(state__name="Gujarat", name="Kadi").exists())
        self.assertFalse(City.objects.filter(state__name="Rajasthan", name="Badli").exists())

    def test_command_dry_run_writes_nothing(self):
        """Run: tests/test_load_geo_data.py::LoadGeoDataCommandTest::test_command_dry_run_writes_nothing"""
        call_command("load_geo_data", csv=self.csv_path, dry_run=True)

        self.assertFalse(Pincode.objects.filter(code="382230").exists())
        self.assertFalse(City.objects.filter(name="Kadi").exists())

    def test_command_rejects_an_unusable_file(self):
        """Run: tests/test_load_geo_data.py::LoadGeoDataCommandTest::test_command_rejects_an_unusable_file"""
        with self.assertRaises(CommandError):
            call_command("load_geo_data", csv=self.csv_path, states=["Kerala"])
