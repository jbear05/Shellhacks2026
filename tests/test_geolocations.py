"""The committed Geolocator output in data/processed/: it agrees with the points the
organizers give in Projects_Overlaps.xlsx, and it was written with the current overrides."""

import csv
from pathlib import Path

import pytest

import gridlock_desc_locator as locator

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"
DESC = "Dominion Energy South Carolina"
GEORGIA = "Georgia Power"

# (utility, project_id, target_location, latitude, longitude), from the table in
# docs/challenge.md. The sheet has no point for Hooks, Ft Johnson or Purrysburg.
KNOWN_POINTS = [
    (DESC, "6809 E", "Stevens Creek", 33.56260, -82.05136),
    (DESC, "6810 A", "Thurmond", 33.66013, -82.19593),
    (DESC, "06367 D-G", "Jasper", 32.35912, -81.12460),
    (DESC, "06367 D-G", "Okatie", 32.33376, -81.03249),
    (DESC, "6808 S", "Bluffton", 32.23503, -80.85338),
    (DESC, "6807 B", "Queensboro", 32.72279, -79.96733),
    (GEORGIA, "20793", "EVANS PRIMARY", 33.54399, -82.16865),
    (GEORGIA, "20793", "THURMOND DAM", 33.66013, -82.19593),
    (GEORGIA, "20277", "MCINTOSH", 32.35212, -81.17511),
    (GEORGIA, "20065", "MCINTOSH", 32.35212, -81.18211),  # the sheet's two McIntosh points are 0.4 miles apart
    (GEORGIA, "20065", "GOSHEN", 32.24870, -81.20947),
    (GEORGIA, "18492", "MITCHELL", 31.44712, -84.13384),
    (GEORGIA, "18492", "NORTH TIFTON", 31.47809, -83.54913),
    (GEORGIA, "11821", "JESUP", 31.60311, -81.92495),
    (GEORGIA, "11821", "LUDOWICI PRIMARY", 31.72160, -81.74370),
]


@pytest.fixture(scope="module")
def locations():
    rows = []
    for prefix in ("desc", "georgia_power"):
        with open(PROCESSED / f"{prefix}_project_locations.csv", newline="", encoding="utf-8-sig") as file:
            rows.extend(csv.DictReader(file))
    return rows


@pytest.mark.parametrize("utility, project_id, name, latitude, longitude", KNOWN_POINTS)
def test_the_organizers_points_are_within_a_mile(locations, utility, project_id, name, latitude, longitude):
    [row] = [
        row for row in locations
        if (row["utility"], row["project_id"], row["target_location"]) == (utility, project_id, name)
    ]
    assert locator.haversine_miles(latitude, longitude, row["latitude"], row["longitude"]) < 1


def test_every_override_is_in_the_output(locations):
    # Fails when the overrides changed but the Geolocator wasn't run again.
    for (utility, project_id, name), override in locator.OVERRIDES.items():
        rows = [
            row for row in locations
            if row["utility"] == utility and row["target_location"].lower() == name
            and project_id in ("", row["project_id"])
        ]
        assert rows, f"no location matches the override {(utility, project_id, name)}"
        for row in rows:
            assert row["source"] == "Manual override"
            if not project_id and locator.OVERRIDES.get((utility, row["project_id"], name)):
                continue  # a project's own override wins over this one
            assert (row["latitude"], row["longitude"]) == (override["latitude"], override["longitude"])
