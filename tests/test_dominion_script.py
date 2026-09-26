"""Tests against the real 44-page Dominion project descriptions PDF (under a second to parse)."""

import pytest

import dominionScript as ds

pytestmark = pytest.mark.skipif(not ds.DEFAULT_PDF.is_file(), reason="Dominion project descriptions PDF not present")


@pytest.fixture(scope="module")
def projects():
    return {project["project_id"]: project for project in ds.extract_utility_projects(ds.DEFAULT_PDF)}


def test_reads_one_project_per_page(projects):
    assert len(projects) == 44


def test_ids_are_spelled_like_the_geolocator_list(projects):
    # The PDF writes "06367 A - C, H" and "06367 D - G"
    assert {"06367 A-C, H", "06367 D-G"} <= set(projects)


def test_in_service_date_is_iso_and_the_last_phase(projects):
    assert projects["6807 B"]["in_service_date"] == "2023-12-31"
    assert projects["6859"]["in_service_date"] == "2026-10-01"  # "10/1/2025 (phase 1) and 10/1/2026 (phase 2)"


def test_start_date_is_the_first_year_with_spending(projects):
    assert projects["06810 F"]["start_date"] == "2026-01-01"
    assert projects["6807 B"]["start_date"] == ""  # spent before 2024


def test_title_dashes_are_hyphens(projects):
    assert projects["6359"]["project_name"].startswith("Yemassee- Ritter")


def test_miles_come_from_the_title_or_description(projects):
    assert projects["06076A"]["line_miles"] == 18.0  # title: "(Approx 18 Miles)"
    assert projects["6809 E"]["line_miles"] == 9.5  # description: "9.5 miles."
