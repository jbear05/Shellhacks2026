"""Unit tests for parsers.georgia_power, using text samples copied from pypdf's output for the IRP."""

import csv
import dataclasses
import re
from datetime import date
from types import SimpleNamespace

import pytest

from parsers import georgia_power as gp

BANNER = (
    "CRITICAL ENERGY INFRASTRUCTURE INFORMATION - CONFIDENTIAL. This data is confidential CEII and is "
    "subject to Regulation by CFR Sec. 388.113.  Recipient should \nbe aware that disclosure of this "
    "material and its contents shall be handled in accordance with CEII procedures. Any and all "
    "duplications of this data must contain this \nnotification. This document contains non-public "
    "transmission information and in accordance with FERC policy, should not be disclosed to Marketing "
    "Function \nemployees. \n \n2024 GA ITS Ten-Year Plan (2025-2034)                    Page 19 of 304 \n"
)
TABLE_HEADER = (
    "Zone Year TEAMS \nNumber Project Name Need Date \n2024 \nProject \nSponsor Estimated Cost - GPC "
    "Estimated Cost - GTC Estimated Cost - \nMEAG \nEstimated Cost - \nDU Totals \n"
)

TABLE_PAGE_1 = """\
A.  Georgia ITS 10 Year Expansion Plan Projects List
Table 2 Georgia ITS 10 Year Plan Project List
219 2025 19523 SAV: CC - HYUNDAI MOTORS
SAVANNAH AKA. PROJECT EA
1/1/2025 SAV REDACTED  REDACTED  REDACTED  REDACTED  REDACTED
215 2033 20793 EVANS PRIMARY -
THURMOND DAM (USA) #5
PUBLIC DISCLOSURE"""
TABLE_PAGE_2 = f"""{BANNER}{TABLE_HEADER}115KV REBUILD
6/1/2033 GPC REDACTED  REDACTED  REDACTED  REDACTED  REDACTED
Total      REDACTED REDACTED REDACTED REDACTED REDACTED
B. Cancelled Projects List
214 2031 12016 ARKWRIGHT - LLOYD SHOALS 115
KV LINE RECONDUCTOR
6/1/2024 GPC REDACTED  REDACTED  REDACTED  REDACTED  REDACTED  REDACTED
"""

DETAIL_PAGE = """\
EVANS PRIMARY - THURMOND DAM (USA) #5 115KV REBUILD
Teams # 20793
Need Date 06/01/2033 Start Date 06/01/2029
Description

Supporting Statement

Change From Previous Ten Year Plan

Change From Previous IRP

Estimated Cost – GPC   REDACTED
Estimated Cost – GTC   REDACTED
Estimated Cost – MEAG   REDACTED
Estimated Cost – DU   REDACTED
Estimated Cost – ITS
Assigned*
REDACTED
* The ITS Assigned designation is for parity forecast purposes only

Rebuild approximately 5.45 miles of Euchee Creek - Thurmond Dam segment of the Evans Primary -
Thurmond Dam (USA) #5 115kV line with 200C 1351 ACSS Martin conductor.

REDACTED

New Project
New Project
"""
# East Walton's description is long enough that the rest of its cost block lands on the next page.
SPILLOVER_PAGE_1 = """\
GTC: EAST WALTON 500/230KV PROJECT
Teams # 09662
Need Date 06/01/2027 Start Date 06/01/2023
Description

Supporting Statement

Change From Previous Ten Year Plan

Change From Previous IRP

Estimated Cost – GPC   REDACTED
Estimated Cost – GTC   REDACTED
GTC:
 - Construct the East Walton 500/230kV substation.
 - Construct the Bostwick 230kV switching station.
MEAG:
 - Construct the Jack's Creek 230kV switching station.
REDACTED
No Change
New Project
"""
SPILLOVER_PAGE_2 = """\
Estimated Cost – MEAG   REDACTED
Estimated Cost – DU   REDACTED
Estimated Cost – ITS
Assigned*
REDACTED
* The ITS Assigned designation is for parity forecast purposes only
"""
NEXT_DETAIL_PAGE = DETAIL_PAGE.replace("20793", "20794").replace("#5", "#6")


def table_doc(*pages: str) -> gp.PagedText:
    return gp.join_pages([gp.clean_page_text(page) for page in pages], first_page=189)


def make_row(teams="20793", name="EVANS PRIMARY - THURMOND DAM (USA) #5 115KV REBUILD", sponsor="GPC"):
    return gp.TableRow(
        teams=teams, zone="215", plan_year=2033, name=name,
        need_date=date(2033, 6, 1), sponsor=sponsor, page=190,
    )


def make_detail(teams="20793", description="Rebuild approximately 5.45 miles of line.", need=date(2033, 6, 1)):
    return gp.ProjectDetail(
        teams=teams, need_date=need, start_date=date(2029, 6, 1), description=description,
        change_from_previous_plan="New Project", change_from_previous_irp="New Project", page=410,
    )


# --------------------------------------------------------------------------- page text

def test_clean_page_text_removes_repeated_boilerplate():
    cleaned = gp.clean_page_text(TABLE_PAGE_2)
    for fragment in ("CRITICAL ENERGY", "Page 19 of 304", "Estimated Cost", "PUBLIC DISCLOSURE"):
        assert fragment not in cleaned
    assert cleaned.lstrip().startswith("115KV REBUILD")


def test_paged_text_maps_offsets_to_pdf_pages():
    doc = gp.join_pages(["first", "second"], first_page=177)
    assert doc.page_at(0) == 177
    assert doc.page_at(doc.text.index("second")) == 178


class FakeReader:
    """Just enough of pypdf's PdfReader for bookmarked_page_range."""

    def __init__(self, outline, page_count):
        self.outline = outline
        self.pages = [None] * page_count

    def get_destination_page_number(self, bookmark):
        return bookmark.page - 1


def bookmark(title, page):
    return SimpleNamespace(title=title, page=page)


def test_bookmarked_page_range_ends_before_next_bookmark():
    outline = [
        bookmark("Index & Foreword", 2),
        [bookmark("V3D1_Title Page.pdf", 170)],  # nested bookmarks are flattened
        bookmark("2 - 2024 GA ITS Ten Year Plan - Public Disclosure.pdf", 171),
        bookmark("V3D2_Title Page.pdf", 475),
    ]
    assert gp.bookmarked_page_range(FakeReader(outline, 668), gp.SECTION_BOOKMARK) == (171, 474)


def test_bookmarked_page_range_runs_to_last_page_for_final_bookmark():
    reader = FakeReader([bookmark("Index", 1), bookmark("GA ITS Ten Year Plan", 171)], 668)
    assert gp.bookmarked_page_range(reader, gp.SECTION_BOOKMARK) == (171, 668)


def test_bookmarked_page_range_requires_matching_bookmark():
    with pytest.raises(gp.ParseError, match="no bookmark"):
        gp.bookmarked_page_range(FakeReader([bookmark("Index", 1)], 10), gp.SECTION_BOOKMARK)


# --------------------------------------------------------------------------- Table 2

def test_parse_project_table_rejoins_wrapped_names_across_pages():
    rows = gp.parse_project_table(table_doc(TABLE_PAGE_1, TABLE_PAGE_2))

    assert [row.teams for row in rows] == ["19523", "20793"]
    hyundai, evans = rows
    assert hyundai.name == "SAV: CC - HYUNDAI MOTORS SAVANNAH AKA. PROJECT EA"
    assert (hyundai.sponsor, hyundai.need_date, hyundai.page) == ("SAV", date(2025, 1, 1), 189)
    assert evans.name == "EVANS PRIMARY - THURMOND DAM (USA) #5 115KV REBUILD"
    assert (evans.zone, evans.plan_year, evans.need_date) == ("215", 2033, date(2033, 6, 1))


def test_parse_project_table_stops_at_total_row():
    rows = gp.parse_project_table(table_doc(TABLE_PAGE_1, TABLE_PAGE_2))
    assert "12016" not in {row.teams for row in rows}


def test_parse_project_table_fails_loudly_on_incomplete_row():
    broken = TABLE_PAGE_1.replace("1/1/2025 SAV", "SAV")  # row loses its need date
    with pytest.raises(gp.ParseError, match="row starts"):
        gp.parse_project_table(table_doc(broken, TABLE_PAGE_2))


def test_parse_project_table_reports_impossible_dates_as_parse_errors():
    bad_date = TABLE_PAGE_1.replace("1/1/2025 SAV", "13/1/2025 SAV")
    with pytest.raises(gp.ParseError, match="TEAMS 19523"):
        gp.parse_project_table(table_doc(bad_date, TABLE_PAGE_2))


def test_parse_project_table_requires_caption_and_total_row():
    with pytest.raises(gp.ParseError, match="caption"):
        gp.parse_project_table(table_doc(TABLE_PAGE_2))
    with pytest.raises(gp.ParseError, match="Total"):
        gp.parse_project_table(table_doc(TABLE_PAGE_1))


# --------------------------------------------------------------------------- detail pages

def test_parse_details_reads_values_printed_after_labels():
    detail = gp.parse_details(gp.join_pages([DETAIL_PAGE], first_page=410))["20793"]

    assert (detail.need_date, detail.start_date) == (date(2033, 6, 1), date(2029, 6, 1))
    assert detail.description.startswith("Rebuild approximately 5.45 miles of Euchee Creek")
    assert detail.description.endswith("ACSS Martin conductor.")
    assert (detail.change_from_previous_plan, detail.change_from_previous_irp) == ("New Project", "New Project")
    assert detail.page == 410


def test_parse_details_handles_cost_block_spilling_onto_next_page():
    doc = gp.join_pages([SPILLOVER_PAGE_1, SPILLOVER_PAGE_2, NEXT_DETAIL_PAGE], first_page=301)
    details = gp.parse_details(doc)

    assert set(details) == {"09662", "20794"}
    walton = details["09662"]
    assert walton.description.startswith("GTC: - Construct the East Walton 500/230kV substation.")
    assert walton.description.endswith("Jack's Creek 230kV switching station.")
    assert (walton.change_from_previous_plan, walton.change_from_previous_irp) == ("No Change", "New Project")
    assert details["20794"].page == 303


def test_parse_details_fails_loudly_without_supporting_statement():
    broken, removed = re.subn(r"conductor\.\s*REDACTED", "conductor.", DETAIL_PAGE)
    assert removed == 1
    with pytest.raises(gp.ParseError, match="20793"):
        gp.parse_details(gp.join_pages([broken], first_page=410))


def test_parse_details_rejects_duplicate_projects():
    with pytest.raises(gp.ParseError, match="more than one detail page"):
        gp.parse_details(gp.join_pages([DETAIL_PAGE, DETAIL_PAGE], first_page=410))


# --------------------------------------------------------------------------- titles

@pytest.mark.parametrize(
    ("title", "locations", "project_type", "owner_tags"),
    [
        ("EVANS PRIMARY - THURMOND DAM (USA) #5 115KV REBUILD", ("EVANS PRIMARY", "THURMOND DAM"), "LINE", ("USA",)),
        ("SAV: MCINTOSH - PURRYSBURG 230KV REACTORS", ("MCINTOSH", "PURRYSBURG"), "LINE", ()),
        ("ECHECONNEE-WELLSTON 115KV REBUILD", ("ECHECONNEE", "WELLSTON"), "LINE", ()),
        ("GTC: BONAIRE PRI- ECHECONNEE 115 KV PARTIAL REBUILD", ("BONAIRE PRIMARY", "ECHECONNEE"), "LINE", ()),
        ("GTC: GARRETT RD - V. RICA 230KV LINE RECONDUCTOR (CC NET IM)", ("GARRETT ROAD", "VILLA RICA"), "LINE", ()),
        ("GRID - BREMEN - CROOKED CREEK (APC) 115 KV PROJECT", ("BREMEN", "CROOKED CREEK"), "LINE", ("APC",)),
        ("FARLEY (APC)-TAZEWELL 500KV", ("FARLEY", "TAZEWELL"), "LINE", ("APC",)),
        ("GORDON-N DUBLIN 115KV (GORDON-ENGL MCI J) REBUILD", ("GORDON", "NORTH DUBLIN"), "LINE", ()),
        ("JEFFERSON STREET#3 - NORTHWEST (WHITE) 115 KV RECONDUCTOR", ("JEFFERSON STREET", "NORTHWEST"), "LINE", ()),
        ("GTC: CLIFTONDALE - LINE CREEK 230KV LINE", ("CLIFTONDALE", "LINE CREEK"), "LINE", ()),
        ("GTC: EAST MOULTRIE - HIGHWAY 112 230 KV LINE", ("EAST MOULTRIE", "HIGHWAY 112"), "LINE", ()),
        ("GTC: SWITCH WAY - THORNTON ROAD 230KV LINE REBUILD", ("SWITCH WAY", "THORNTON ROAD"), "LINE", ()),
        ("NEW CAVENDER DRIVE - TRIBUTARY 230KV LINE", ("NEW CAVENDER DRIVE", "TRIBUTARY"), "LINE", ()),
        ("GTC: ROCKVILLE - TIGER CREEK -WARTHEN 500KV LINES", ("ROCKVILLE", "TIGER CREEK", "WARTHEN"), "MULTI_LINE", ()),
        ("NORCROSS 230KV BUS 1-3 SERIES BUS TIE BREAKER INSTALLATION", ("NORCROSS",), "SUBSTATION", ()),
        ("THOMASTON 230 NEW BUILD SUB", ("THOMASTON",), "SUBSTATION", ()),
        ("PLANT YATES BREAKER AND HALF STATION", ("PLANT YATES",), "SUBSTATION", ()),
        ("SMART VALVES AT EAST VILLA RICA SWITCHING STATION", ("EAST VILLA RICA",), "SUBSTATION", ()),
        ("SAV: CC - HYUNDAI MOTORS SAVANNAH AKA. PROJECT EA", ("HYUNDAI MOTORS SAVANNAH",), "SUBSTATION", ()),
        ("THALMANN AND COLERAIN 23O KV LINE RELAY PANEL UPGRADES", ("THALMANN", "COLERAIN"), "MULTI_SITE", ()),
        ("CC - HILL VIEW & GRASSY HOLLOW SUB - CC IMPROVEMENTS", ("HILL VIEW", "GRASSY HOLLOW"), "MULTI_SITE", ()),
        (
            "BAINBRIDGE TRANSMISSION: EAST RIVER ROAD, EAST BAINBRIDGE",
            ("BAINBRIDGE", "EAST RIVER ROAD", "EAST BAINBRIDGE"),
            "MULTI_SITE",
            (),
        ),
        ("DOYLE - LG&E MONROE 230KV - JACKS CREEK LOOP IN", ("DOYLE", "LG&E MONROE"), "BOTH", ()),
        ("XYZ BUS-TIE REPLACEMENT", ("XYZ",), "SUBSTATION", ()),  # hyphenated work word, no voltage
        ("SMART VALVE INSTALLATION", (), "UNKNOWN", ()),
    ],
)
def test_parse_title(title, locations, project_type, owner_tags):
    info = gp.parse_title(title)
    assert info.locations == locations
    assert info.project_type == project_type
    assert info.owner_tags == owner_tags


def test_parse_title_voltages():
    assert gp.parse_title("GTC: CAMDEN INDUSTRIAL PARK 230/115KV NEW SUBSTATION").voltages == (230_000, 115_000)
    assert gp.parse_title("THALMANN AND COLERAIN 23O KV LINE RELAY PANEL UPGRADES").voltages == (230_000,)
    assert gp.parse_title("SMART VALVE INSTALLATION").voltages == ()


# --------------------------------------------------------------------------- records

def test_build_records_joins_detail_and_derives_columns():
    [record] = gp.build_records([make_row()], {"20793": make_detail()})

    assert (record.project_id, record.utility, record.state) == ("20793", "Georgia Power", "Georgia")
    assert (record.location_1, record.location_2, record.location_3) == ("EVANS PRIMARY", "THURMOND DAM", "")
    assert (record.voltage_1, record.voltage_2) == (115_000, None)
    assert (record.line_miles, record.miles_mentioned) == (5.45, "5.45")
    assert (record.start_date, record.detail_page, record.owner_tags) == (date(2029, 6, 1), 410, "USA")


def test_build_records_leaves_line_miles_blank_when_ambiguous():
    detail = make_detail(description="Rebuild the first section (approximately 1.5 miles) and the second (6 miles).")
    [record] = gp.build_records([make_row()], {"20793": detail})
    assert record.line_miles is None
    assert record.miles_mentioned == "1.5; 6"


def test_build_records_takes_voltage_from_description_when_title_has_none():
    row = make_row(teams="20466", name="SMART VALVE INSTALLATION")
    detail = make_detail(teams="20466", description="Install smart valves on the 230kV line.")
    [record] = gp.build_records([row], {"20466": detail})
    assert record.voltage_1 == 230_000


def test_build_records_without_detail_page():
    [record] = gp.build_records([make_row()], {})
    assert (record.start_date, record.description, record.detail_page) == (None, "", None)


def test_find_inconsistencies():
    rows = [make_row(), make_row(teams="11111")]
    details = {"20793": make_detail(need=date(2033, 12, 31)), "99999": make_detail(teams="99999")}

    problems = gp.find_inconsistencies(rows, details)

    assert problems == [
        "TEAMS 20793: need date is 2033-06-01 in Table 2 but 2033-12-31 on its detail page (using Table 2)",
        "TEAMS 11111: no detail page",
        "TEAMS 99999: detail page but no Table 2 row",
    ]


def test_find_inconsistencies_reports_every_problem_with_a_row():
    rows = [make_row(sponsor="XYZ")]
    details = {"20793": make_detail(description="", need=date(2033, 12, 31))}

    problems = gp.find_inconsistencies(rows, details)

    assert [problem.split(": ", 1)[1].split(" ")[0] for problem in problems] == ["need", "empty", "unknown"]


def test_write_csv_round_trip(tmp_path):
    out = tmp_path / "nested" / "projects.csv"
    gp.write_csv(gp.build_records([make_row()], {"20793": make_detail()}), out)

    with out.open(encoding="utf-8", newline="") as handle:
        [row] = list(csv.DictReader(handle))
    assert list(row) == [field.name for field in dataclasses.fields(gp.ProjectRecord)]
    assert (row["voltage_1"], row["voltage_2"], row["in_service_date"]) == ("115000", "", "2033-06-01")


# --------------------------------------------------------------------------- CLI

@pytest.fixture
def fake_pdf(tmp_path):
    pdf = tmp_path / "irp.pdf"
    pdf.write_bytes(b"%PDF-1.7")
    return pdf


def test_main_filters_sponsors(tmp_path, fake_pdf, monkeypatch):
    records = gp.build_records([make_row(), make_row(teams="12345", sponsor="GTC")], {})
    monkeypatch.setattr(gp, "parse_georgia_power", lambda path: records)
    out = tmp_path / "out.csv"

    assert gp.main(["--pdf", str(fake_pdf), "--out", str(out), "--sponsors", "GPC", "SAV"]) == 0
    with out.open(encoding="utf-8", newline="") as handle:
        assert [row["project_id"] for row in csv.DictReader(handle)] == ["20793"]


def test_main_returns_error_code_without_writing_on_parse_error(tmp_path, fake_pdf, monkeypatch):
    def layout_changed(path):
        raise gp.ParseError("layout changed")

    monkeypatch.setattr(gp, "parse_georgia_power", layout_changed)
    out = tmp_path / "out.csv"

    assert gp.main(["--pdf", str(fake_pdf), "--out", str(out)]) == 1
    assert not out.exists()


def test_main_returns_error_code_for_unreadable_pdf(tmp_path, fake_pdf):
    assert gp.main(["--pdf", str(fake_pdf), "--out", str(tmp_path / "out.csv")]) == 1


def test_main_returns_error_code_when_output_cannot_be_written(tmp_path, fake_pdf, monkeypatch):
    monkeypatch.setattr(gp, "parse_georgia_power", lambda path: gp.build_records([make_row()], {}))
    # The output path is an existing directory, so opening it for writing fails like a locked file.
    assert gp.main(["--pdf", str(fake_pdf), "--out", str(tmp_path)]) == 1


def test_main_rejects_missing_pdf(tmp_path):
    with pytest.raises(SystemExit) as exit_info:
        gp.main(["--pdf", str(tmp_path / "missing.pdf")])
    assert exit_info.value.code == 2
