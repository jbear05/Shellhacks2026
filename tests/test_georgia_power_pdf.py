"""Integration tests against the real 2025 IRP Volume 3 PDF (about 10 seconds to parse)."""

from collections import Counter
from datetime import date

import pytest
from pypdf import PdfReader

from parsers import georgia_power as gp

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not gp.DEFAULT_PDF.is_file(), reason="Georgia Power IRP PDF not present"),
]


@pytest.fixture(scope="module")
def parsed():
    doc = gp.load_plan_text(gp.DEFAULT_PDF)
    return gp.parse_project_table(doc), gp.parse_details(doc)


@pytest.fixture(scope="module")
def records(parsed):
    return {record.project_id: record for record in gp.build_records(*parsed)}


def test_ten_year_plan_is_found_by_bookmark():
    assert gp.bookmarked_page_range(PdfReader(gp.DEFAULT_PDF), gp.SECTION_BOOKMARK) == (171, 474)


def test_every_project_is_parsed_and_joined(records):
    assert len(records) == 208
    assert all(record.detail_page is not None and record.description for record in records.values())
    assert Counter(record.sponsor for record in records.values()) == {"GPC": 122, "GTC": 54, "SAV": 16, "MEAG": 14, "DU": 2}


def test_known_project(records):
    evans = records["20793"]
    assert evans.project_name == "EVANS PRIMARY - THURMOND DAM (USA) #5 115KV REBUILD"
    assert (evans.location_1, evans.location_2, evans.project_type) == ("EVANS PRIMARY", "THURMOND DAM", "LINE")
    assert (evans.in_service_date, evans.start_date) == (date(2033, 6, 1), date(2029, 6, 1))
    assert (evans.voltage_1, evans.line_miles, evans.owner_tags) == (115_000, 5.45, "USA")
    assert evans.detail_page == 410


def test_detail_spanning_two_pages_does_not_swallow_the_next_project(records):
    walton = records["09662"]
    assert walton.description.startswith("GTC: - Construct the East Walton 500/230kV substation.")
    assert "Estimated Cost" not in walton.description
    assert records["20505"].description.startswith("GTC will reconductor")


def test_source_inconsistencies_are_reported(parsed):
    problems = gp.find_inconsistencies(*parsed)
    assert [problem.split(":")[0] for problem in problems] == ["TEAMS 19523", "TEAMS 20684", "TEAMS 17900"]
