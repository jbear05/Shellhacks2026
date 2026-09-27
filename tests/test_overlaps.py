import math

import pandas as pd
import pytest

from frontend.analysis import calculate_overlaps, haversine_miles
from frontend.data_loader import _normalize_projects
from frontend.project_data import DESC, GEORGIA, ROOT, load_demo_projects
from ranking import rank_overlaps


@pytest.fixture(scope="module")
def demo():
    return load_demo_projects()


def test_organizers_six_pairs_and_negative_projects(demo):
    result = calculate_overlaps(demo, DESC, GEORGIA)
    lookup = {(r.project_id_a, r.project_id_b): r for r in result.itertuples()}
    for desc, ga, miles, days in [
        ("6810 A", "20793", 3.91, 3074), ("06367 D-G", "20277", 8.38, 152),
        ("06367 D-G", "20065", 7.40, 517), ("6809 E", "20793", 4.40, 3074),
        ("6808 S", "20277", 13.13, 365), ("6808 S", "20065", 14.60, 730),
    ]:
        row = lookup[desc, ga]
        # Regression values from the committed locations; sheet coordinates are tested separately.
        # The sheet has no Hooks point, so its 6810 A and 6809 E centers are one substation;
        # ours are midpoints with Hooks (docs/challenge.md).
        assert row.distance_miles == pytest.approx(miles, abs=0.01)
        assert row.days_apart == days
    assert "6807 B" not in set(result.project_id_a)
    assert not {"18492", "11821"}.intersection(result.project_id_b)


def test_haversine_reproduces_the_organizers_sheet_distances():
    def midpoint(a, b):
        return tuple((x + y) / 2 for x, y in zip(a, b))
    desc = {
        "6810 A": (33.66013, -82.19593),
        "6809 E": (33.56260, -82.05136),
        "06367 D-G": midpoint((32.35912, -81.12460), (32.33376, -81.03249)),
        "6808 S": midpoint((32.33376, -81.03249), (32.23503, -80.85338)),
    }
    ga = {
        "20793": midpoint((33.54399, -82.16865), (33.66013, -82.19593)),
        "20277": (32.35212, -81.17511),
        "20065": midpoint((32.35212, -81.18211), (32.24870, -81.20947)),
    }
    for a, b, miles in [("6810 A", "20793", 4.09), ("06367 D-G", "20277", 5.65),
                         ("06367 D-G", "20065", 7.55), ("6809 E", "20793", 8.01),
                         ("6808 S", "20277", 14.34), ("6808 S", "20065", 14.81)]:
        assert round(haversine_miles(*desc[a], *ga[b]), 2) == miles


def test_exclusions_and_confidence_filter(demo):
    original = calculate_overlaps(demo, DESC, GEORGIA)
    first = original.iloc[0]
    edited = demo.copy()
    edited.loc[(edited.Utility == DESC) & (edited["Project ID"] == first.project_id_a), "Match Status"] = "Excluded"
    assert first.project_id_a not in set(calculate_overlaps(edited, DESC, GEORGIA).project_id_a)
    reliable = calculate_overlaps(demo, DESC, GEORGIA, include_low=False)
    assert not (reliable[["confidence_a", "confidence_b"]] == "Low").any().any()


def test_distance_filter_uses_unrounded_distance():
    longitude = math.degrees(25.004 / 3958.8)
    projects = pd.DataFrame([
        dict(project_id="1", project_name="A", utility="A", lat=0, lon=0),
        dict(project_id="1", project_name="B", utility="B", lat=0, lon=longitude),
    ])
    result = _normalize_projects(projects, "", "test.csv")
    assert calculate_overlaps(result, "A", "B").empty
    assert len(calculate_overlaps(result, "A", "B", threshold=25.01)) == 1
    assert haversine_miles(0, 0, 0, 180) == pytest.approx(math.pi * 3958.8)


def test_synthetic_overlap_fixture():
    directory = ROOT / "frontend" / "test_data" / "overlap_case"
    frames = []
    for utility in ("a", "b"):
        path = directory / f"utility_{utility}_overlapping_projects.csv"
        frames.append(_normalize_projects(pd.read_csv(path, dtype=str, keep_default_na=False), utility, path.name))
    projects = pd.concat(frames, ignore_index=True)
    utilities = projects.Utility.unique()
    result = calculate_overlaps(projects, *utilities)
    assert len(result) == 3
    expected = pd.read_csv(directory / "expected_overlaps.csv")
    for row in result.itertuples():
        target = expected[(expected["Utility A Project"] == row.project_name_a) & (expected["Utility B Project"] == row.project_name_b)].iloc[0]
        assert row.distance_miles == pytest.approx(target["Distance Miles"], abs=0.02)
        assert row.days_apart == target["Date Gap Days"]


def test_ranking_can_prioritize_distance_over_other_scores():
    close = dict(project_id_a="close", distance_miles="4", utility_a="Other", utility_b="Other B")
    farther = dict(project_id_a="far", distance_miles="20", utility_a="Other", utility_b="Other B", start_date_a="2025-01-01", start_date_b="2025-01-01", in_service_date_a="2026-01-01", in_service_date_b="2026-01-01", voltage_a="115000", voltage_b="115000", project_type_a="LINE", project_type_b="LINE")
    assert rank_overlaps([farther, close], mode="distance_first")[0]["project_id_a"] == "close"
    assert rank_overlaps([farther, close], mode="score")[0]["project_id_a"] == "far"


def test_unknown_start_is_not_treated_as_a_confirmed_overlap():
    pair = dict(utility_a="Other", utility_b=GEORGIA, in_service_date_a="2026-01-01", in_service_date_b="2026-06-01", start_date_b="2025-01-01")
    assert "unavailable" in rank_overlaps([pair])[0]["ranking_reason"]
    pair["utility_a"] = DESC
    assert "build windows overlap" in rank_overlaps([pair])[0]["ranking_reason"]
    pair["start_date_a"] = "bad date"
    assert "inconsistent" in rank_overlaps([pair])[0]["ranking_reason"]
