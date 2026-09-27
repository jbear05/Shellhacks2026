"""Clean the synthetic test project CSVs in data/test/raw/.

A teammate added two made-up project lists (PR #8) for testing the stages after the
parsers without the PDFs: 65 DESC projects with no coordinates, and 100 Duke Energy
Carolinas projects with coordinates. Nothing in them comes from a source PDF.

Their rows have more values than their headers have columns: a stray blank after
`other_locations`, another after `owner_tags`, and in the Duke file's single-location
rows a third after `location_2_lon`. Every reader shifts the columns after them.
This script drops those blanks and writes voltages as whole volts (`230000`, not
`230000.0`), which the Geolocator's voltage match needs. Every other value is copied
unchanged. Problems in the data are logged, not fixed.

Run from the repository root:

    python clean_test_csvs.py
"""

from __future__ import annotations

import argparse
import csv
import logging
import math
from collections import Counter
from collections.abc import Sequence
from datetime import date
from pathlib import Path

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_RAW_DIR = REPO_ROOT / "data" / "test" / "raw"
DEFAULT_OUT_DIR = REPO_ROOT / "data" / "test"

# Raw file name -> cleaned file name.
FILES = {
    "code.csv": "desc_test_projects.csv",
    "dukeEnergyCarolinas.csv": "duke_test_projects.csv",
}

# The columns of data/processed/georgia_power_projects.csv, so the cleaned files can go
# to gridlock_desc_locator.py --projects-csv.
BASE_COLUMNS = [
    "project_id", "utility", "sponsor", "state", "project_name", "project_type",
    "location_1", "location_2", "location_3", "other_locations", "voltage_1", "voltage_2",
    "in_service_date", "start_date", "plan_year", "zone", "owner_tags", "line_miles",
    "miles_mentioned", "description", "change_from_previous_plan", "change_from_previous_irp",
    "detail_need_date", "table_page", "detail_page",
]
COORDINATE_COLUMNS = [
    "location_1_lat", "location_1_lon", "location_2_lat", "location_2_lon",
    "center_lat", "center_lon", "confidence_score",
]
# The column each stray blank follows, in the order they appear in a row. A row with
# N extra values has the first N of them.
STRAY_BLANK_AFTER = ("other_locations", "owner_tags", "location_2_lon")

DATE_COLUMNS = ("in_service_date", "start_date", "detail_need_date")
VOLTAGE_COLUMNS = ("voltage_1", "voltage_2")
INTEGER_COLUMNS = ("plan_year", "table_page", "detail_page")
PROJECT_TYPES = {"LINE", "SUBSTATION", "BOTH", "MULTI_LINE", "MULTI_SITE", "UNKNOWN"}
CONFIDENCES = {"HIGH", "MEDIUM", "LOW"}
# Contiguous US, so a longitude read as a latitude (or the reverse) fails.
LATITUDE_RANGE = (24.0, 50.0)
LONGITUDE_RANGE = (-125.0, -66.0)
STATION_WORDS = ("SUBSTATION", "SWITCHING STATION", "SWITCHYARD", "TRANSFORMER")


class StructureError(ValueError):
    """The file's layout isn't the one this script knows how to fix."""


def realign(header: Sequence[str], row: Sequence[str], where: str) -> list[str]:
    """Drop the stray blanks from one raw row."""
    extra = len(row) - len(header)
    slots = [name for name in STRAY_BLANK_AFTER if name in header]
    if not 0 <= extra <= len(slots):
        raise StructureError(f"{where}: {len(row)} values for {len(header)} columns")
    row = list(row)
    for name in slots[:extra]:
        index = header.index(name) + 1
        if row[index].strip():
            raise StructureError(f"{where}: expected a stray blank after {name}, found {row[index]!r}")
        del row[index]
    return row


def _number(value: str, column: str, where: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise StructureError(f"{where}: {column} is {value!r}, not a number") from None
    if not math.isfinite(number):
        raise StructureError(f"{where}: {column} is {value!r}")
    return number


def clean_record(record: dict[str, str], where: str) -> dict[str, str]:
    """Check each value's type, which catches a row the realignment got wrong, and
    write voltages as whole volts."""
    record = dict(record)
    if not record["project_id"].strip():
        raise StructureError(f"{where}: blank project_id")
    if record["project_type"] not in PROJECT_TYPES:
        raise StructureError(f"{where}: project_type is {record['project_type']!r}")
    for column in DATE_COLUMNS:
        if record[column]:
            try:
                date.fromisoformat(record[column])
            except ValueError:
                raise StructureError(f"{where}: {column} is {record[column]!r}, not a date") from None
    for column in VOLTAGE_COLUMNS:
        if record[column]:
            volts = _number(record[column], column, where)
            if not volts.is_integer() or volts < 1000:
                raise StructureError(f"{where}: {column} is {record[column]!r}, not whole volts")
            record[column] = str(int(volts))
    for column in INTEGER_COLUMNS:
        if record[column] and not record[column].isdigit():
            raise StructureError(f"{where}: {column} is {record[column]!r}, not a whole number")
    if record["line_miles"]:
        _number(record["line_miles"], "line_miles", where)
    for part in filter(None, record["miles_mentioned"].split("; ")):
        _number(part, "miles_mentioned", where)
    if "confidence_score" in record:
        for column, (low, high) in (
            ("location_1_lat", LATITUDE_RANGE), ("location_2_lat", LATITUDE_RANGE), ("center_lat", LATITUDE_RANGE),
            ("location_1_lon", LONGITUDE_RANGE), ("location_2_lon", LONGITUDE_RANGE), ("center_lon", LONGITUDE_RANGE),
        ):
            if record[column] and not low <= _number(record[column], column, where) <= high:
                raise StructureError(f"{where}: {column} is {record[column]}, outside {low} to {high}")
        if record["confidence_score"] and record["confidence_score"].upper() not in CONFIDENCES:
            raise StructureError(f"{where}: confidence_score is {record['confidence_score']!r}")
    return record


def read_raw_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        raise StructureError(f"{path.name} is empty")
    header, body = rows[0], rows[1:]
    if header not in (BASE_COLUMNS, BASE_COLUMNS + COORDINATE_COLUMNS):
        raise StructureError(f"{path.name}: unexpected columns {header}")
    records = []
    for line, row in enumerate(body, start=2):
        if not any(value.strip() for value in row):
            continue
        where = f"{path.name} line {line}"
        values = realign(header, row, where)
        records.append(clean_record(dict(zip(header, values)), f"{where} (project {values[0]})"))
    return header, records


def _miles_between(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 3958.8 * math.asin(math.sqrt(h))


def find_problems(records: Sequence[dict[str, str]]) -> list[str]:
    """Problems in the data itself. They are logged; the values are left as they are."""
    problems = []
    keys = Counter((record["utility"], record["project_id"]) for record in records)
    problems += [f"{project_id}: appears {count} times for {utility}" for (utility, project_id), count in keys.items() if count > 1]
    for record in records:
        project_id, name = record["project_id"], record["project_name"].upper()
        if record["start_date"] and record["in_service_date"] and record["start_date"] > record["in_service_date"]:
            problems.append(f"{project_id}: start_date {record['start_date']} is after in_service_date {record['in_service_date']}")
        if record["project_type"] == "LINE" and any(word in name for word in STATION_WORDS):
            problems.append(f"{project_id}: typed LINE, but the name is station work: {record['project_name']}")
        if record["project_type"] == "SUBSTATION" and (record["location_2"] or record["line_miles"]):
            problems.append(f"{project_id}: typed SUBSTATION, but has a second location or line miles")
        if record.get("location_2_lat") and record.get("location_2_lon"):
            points = [float(record[column]) for column in ("location_1_lat", "location_1_lon", "location_2_lat", "location_2_lon")]
            apart = _miles_between(*points)
            if record["line_miles"] and apart > 2 * float(record["line_miles"]):
                problems.append(
                    f"{project_id}: {record['location_1']} and {record['location_2']} are {apart:.1f} miles apart, "
                    f"for a {record['line_miles']}-mile line"
                )
            midpoint = ((points[0] + points[2]) / 2, (points[1] + points[3]) / 2)
            if record["center_lat"] and _miles_between(*midpoint, float(record["center_lat"]), float(record["center_lon"])) > 0.5:
                problems.append(f"{project_id}: center isn't the midpoint of its two locations")
    return problems


def write_csv(header: Sequence[str], records: Sequence[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(records)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Realign the synthetic test project CSVs.")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR, help="raw files (default: %(default)s)")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="cleaned files (default: %(default)s)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Read and check every file before writing any, so a bad file leaves no partial output.
    cleaned = []
    for raw_name, out_name in FILES.items():
        path = args.raw_dir / raw_name
        try:
            header, records = read_raw_csv(path)
        except (OSError, StructureError) as exc:
            log.error("Could not clean %s: %s", path, exc)
            return 1
        for problem in find_problems(records):
            log.warning("%s %s", raw_name, problem)
        cleaned.append((header, records, args.out_dir / out_name))

    for header, records, out_path in cleaned:
        try:
            write_csv(header, records, out_path)
        except OSError as exc:  # e.g. the CSV is open in Excel
            log.error("Could not write %s: %s", out_path, exc)
            return 1
        log.info("Wrote %d projects to %s", len(records), out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
