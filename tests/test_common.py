from datetime import date

import pytest

from parsers.common import extract_miles, extract_voltages, normalize_text, parse_us_date


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("6/1/2033", date(2033, 6, 1)),
        ("12/31/23", date(2023, 12, 31)),
        (" 06/01/2029 ", date(2029, 6, 1)),
    ],
)
def test_parse_us_date(text, expected):
    assert parse_us_date(text) == expected


def test_parse_us_date_rejects_other_formats():
    with pytest.raises(ValueError):
        parse_us_date("2033-06-01")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("115KV REBUILD", [115_000]),
        ("GTC: HOPEWELL 230/115 KV BANK A", [230_000, 115_000]),
        ("SAV: LITTLE OGEECHEE 230- 115KV: RELAY", [230_000, 115_000]),
        ("Union Pier 115-13.8 kV Sub: Tap", [115_000, 13_800]),
        ("four 230/25kV banks and a 230kV ring bus", [230_000, 25_000]),
        ("NORCROSS 230KV BUS 1-3 SERIES BUS TIE", [230_000]),
        ("SMART VALVE INSTALLATION", []),
    ],
)
def test_extract_voltages(text, expected):
    assert extract_voltages(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Rebuild approximately 5.45 miles of line", [5.45]),
        ("Robins Spring - Kaolin J (2.23mi) and 1 mile more", [2.23, 1.0]),
        ("Bring another 10mile 230kV line", [10.0]),
        ("GTC will construct the ~15 - mile section", [15.0]),
        ("Rebuild the Four Mile tap", []),
    ],
)
def test_extract_miles(text, expected):
    assert extract_miles(text) == expected


def test_normalize_text_collapses_whitespace_and_dashes():
    assert normalize_text(" Queensboro – Ft Johnson\n 115 kV ") == "Queensboro - Ft Johnson 115 kV"
