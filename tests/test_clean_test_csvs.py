"""Tests for clean_test_csvs.py, on rows copied from the raw files in data/test/raw/."""

import csv
import dataclasses

import pytest

import clean_test_csvs as clean
from parsers import georgia_power as gp

BASE_HEADER = ",".join(clean.BASE_COLUMNS)
DUKE_HEADER = ",".join(clean.BASE_COLUMNS + clean.COORDINATE_COLUMNS)

# From raw/code.csv: 27 values for 25 columns.
DESC_LINE = (
    "30007,Dominion Energy South Carolina,DESC,South Carolina,DESC: COLUMBIA NORTH TO BLYTHEWOOD 115KV RECONDUCTOR,"
    "LINE,COLUMBIA NORTH,BLYTHEWOOD,,,,115000.0,,2026-06-01,2024-05-01,2026,Midlands,,,12.5,12.5,"
    "Reconductor 12.5 miles of 115kV line to support residential expansion in northern Richland County.,"
    "Project advanced,Project advanced,2026-06-01,16,26"
)
# From raw/dukeEnergyCarolinas.csv: 34 values for 32 columns, and 35 for a single-location row.
DUKE_LINE = (
    "40001,Duke Energy Carolinas,DEC,North Carolina,DEC: CHARLOTTE CENTER CITY 230KV UNDERGROUND,LINE,CHARLOTTE,"
    "SOUTH END,,,,230000.0,,2025-10-01,2023-01-01,2025,Piedmont,,,4.5,4.5,"
    "Undergrounding existing 230kV transmission line to support downtown Charlotte density.,No Change,No Change,"
    "2025-10-01,10,20,35.2271,-80.8431,35.2110,-80.8590,35.2191,-80.8511,High"
)
DUKE_SUBSTATION = (
    "40003,Duke Energy Carolinas,DEC,South Carolina,DEC: HARTWELL HYDRO 230KV SWITCHYARD UPGRADE,SUBSTATION,"
    "HARTWELL DAM,,,,,230000.0,,2030-06-01,2028-01-01,2030,Upstate,,,,,Upgrade 230kV terminal equipment and "
    "breakers at the Duke Energy side of the Hartwell Dam hydro facility.,New Project,New Project,2030-06-01,12,22,"
    "34.3461,-82.8139,,,,34.3461,-82.8139,High"
)


def _raw(tmp_path, header, *lines, name="raw.csv"):
    path = tmp_path / name
    path.write_text("\n".join([header, *lines]) + "\n", encoding="utf-8")
    return path


def test_base_columns_are_the_georgia_parser_columns():
    # So the cleaned files can go to gridlock_desc_locator.py --projects-csv.
    assert clean.BASE_COLUMNS == [field.name for field in dataclasses.fields(gp.ProjectRecord)]


def test_drops_the_two_stray_blanks_from_a_desc_row(tmp_path):
    _, [record] = clean.read_raw_csv(_raw(tmp_path, BASE_HEADER, DESC_LINE))
    assert record["location_2"] == "BLYTHEWOOD"
    assert record["voltage_1"] == "115000"
    assert record["voltage_2"] == ""
    assert record["in_service_date"] == "2026-06-01"
    assert record["start_date"] == "2024-05-01"
    assert record["zone"] == "Midlands"
    assert record["line_miles"] == "12.5"
    assert record["description"].startswith("Reconductor 12.5 miles")
    assert record["detail_page"] == "26"


def test_drops_a_third_stray_blank_from_a_single_location_duke_row(tmp_path):
    _, [line, substation] = clean.read_raw_csv(_raw(tmp_path, DUKE_HEADER, DUKE_LINE, DUKE_SUBSTATION))
    assert (line["location_2_lat"], line["location_2_lon"]) == ("35.2110", "-80.8590")
    assert (line["center_lat"], line["center_lon"], line["confidence_score"]) == ("35.2191", "-80.8511", "High")
    assert substation["voltage_1"] == "230000"
    assert (substation["location_2_lat"], substation["location_2_lon"]) == ("", "")
    assert (substation["center_lat"], substation["center_lon"]) == ("34.3461", "-82.8139")
    assert substation["confidence_score"] == "High"


def test_a_value_where_a_stray_blank_should_be_is_a_structure_error(tmp_path):
    line = DESC_LINE.replace("BLYTHEWOOD,,,,", "BLYTHEWOOD,,,X,")
    with pytest.raises(clean.StructureError, match="stray blank after other_locations"):
        clean.read_raw_csv(_raw(tmp_path, BASE_HEADER, line))


def test_too_many_values_is_a_structure_error(tmp_path):
    with pytest.raises(clean.StructureError, match="28 values for 25 columns"):
        clean.read_raw_csv(_raw(tmp_path, BASE_HEADER, DESC_LINE + ","))


def test_a_value_of_the_wrong_type_is_a_structure_error(tmp_path):
    # One blank too many before the voltage and one value short at the end: the stray
    # slots are still blank, but every later column shifts.
    line = DESC_LINE.replace("BLYTHEWOOD,,,,", "BLYTHEWOOD,,,,,").rsplit(",", 1)[0]
    with pytest.raises(clean.StructureError, match="detail_need_date is 'Project advanced', not a date"):
        clean.read_raw_csv(_raw(tmp_path, BASE_HEADER, line))


def test_an_unknown_header_is_a_structure_error(tmp_path):
    with pytest.raises(clean.StructureError, match="unexpected columns"):
        clean.read_raw_csv(_raw(tmp_path, BASE_HEADER.replace("zone", "region"), DESC_LINE))


def test_voltages_must_be_whole_volts(tmp_path):
    with pytest.raises(clean.StructureError, match="not whole volts"):
        clean.read_raw_csv(_raw(tmp_path, BASE_HEADER, DESC_LINE.replace("115000.0", "115.5")))


def test_endpoints_far_apart_for_the_line_length_are_a_problem(tmp_path):
    line = (
        "40053,Duke Energy Carolinas,DEC,South Carolina,DEC: CAMDEN TO WILMINGTON 115KV TIE,LINE,CAMDEN,WILMINGTON,"
        ",,,115000.0,,2030-08-01,2028-07-01,2030,Coastal,,,17.4,17.4,Construct new tie between Camden and Wilmington "
        "to improve coastal transfer capability and to support storm hardening goals.,New Project,New Project,"
        "2030-08-01,62,72,34.2455,-80.6105,34.2104,-77.8868,34.2279,-79.2487,Medium"
    )
    _, records = clean.read_raw_csv(_raw(tmp_path, DUKE_HEADER, DUKE_LINE, line))
    assert clean.find_problems(records) == [
        "40053: CAMDEN and WILMINGTON are 155.6 miles apart, for a 17.4-mile line"
    ]


def test_type_problems_are_reported_not_fixed(tmp_path):
    line = DESC_LINE.replace("BLYTHEWOOD 115KV RECONDUCTOR", "BLYTHEWOOD 230KV SWITCHING STATION")
    _, records = clean.read_raw_csv(_raw(tmp_path, BASE_HEADER, line))
    assert clean.find_problems(records) == [
        "30007: typed LINE, but the name is station work: DESC: COLUMBIA NORTH TO BLYTHEWOOD 230KV SWITCHING STATION"
    ]
    assert records[0]["project_type"] == "LINE"


def test_a_structure_error_writes_no_files(tmp_path):
    raw_dir, out_dir = tmp_path / "raw", tmp_path / "out"
    raw_dir.mkdir()
    _raw(raw_dir, BASE_HEADER, DESC_LINE, name="code.csv")
    _raw(raw_dir, DUKE_HEADER, DUKE_LINE + ",", name="dukeEnergyCarolinas.csv")
    assert clean.main(["--raw-dir", str(raw_dir), "--out-dir", str(out_dir)]) == 1
    assert not out_dir.exists()


def test_committed_files_match_a_fresh_run(tmp_path):
    assert clean.main(["--out-dir", str(tmp_path)]) == 0
    for name in clean.FILES.values():
        with (tmp_path / name).open(newline="", encoding="utf-8") as fresh, \
                (clean.DEFAULT_OUT_DIR / name).open(newline="", encoding="utf-8") as committed:
            assert list(csv.reader(fresh)) == list(csv.reader(committed)), name
