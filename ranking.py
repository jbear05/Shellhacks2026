"""Rank Gridlock overlap pairs with a small, explainable scoring model.

The input is an overlap CSV.  Project attributes can be present on each overlap
row, or supplied by one or more project CSVs keyed by (utility, project_id).
"""

from __future__ import annotations

import argparse
import csv
import math
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping, Sequence


OUTPUT_COLUMNS = [
    "distance_score",
    "timeline_overlap_score",
    "days_apart_score",
    "power_voltage_score",
    "project_type_score",
    "total_score",
    "ranking_reason",
]


def _value(row: Mapping[str, str], *names: str) -> str:
    lowered = {key.strip().casefold(): value for key, value in row.items()}
    for name in names:
        value = lowered.get(name.casefold(), "")
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _number(value: str) -> float | None:
    try:
        number = float(value.replace(",", "").strip())
    except (AttributeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _date(value: str) -> date | None:
    try:
        return date.fromisoformat(value.strip())
    except (AttributeError, ValueError):
        return None


def _voltage(value: str) -> float | None:
    """Return voltage in volts, accepting values such as 230000 and 230 kV."""
    if not value:
        return None
    normalized = value.casefold().replace(" ", "")
    number = _number(normalized.replace("kv", ""))
    if number is None:
        return None
    return number * 1000 if "kv" in normalized or number < 1000 else number


def _project_type(value: str) -> str:
    value = value.strip().upper().replace(" ", "_")
    if value in {"LINE", "MULTI_LINE", "TRANSMISSION_LINE"}:
        return "LINE"
    if value in {"SUBSTATION", "STATION"}:
        return "SUBSTATION"
    if value in {"BOTH", "MULTI_SITE"}:
        return "BOTH"
    return ""


def _project_key(row: Mapping[str, str], suffix: str = "") -> tuple[str, str] | None:
    utility = _value(row, f"utility_{suffix}", f"{suffix} utility")
    project_id = _value(row, f"project_id_{suffix}", f"{suffix} project id")
    if utility and project_id:
        return utility, project_id
    return None


def _score_distance(distance: float | None) -> int:
    if distance is None:
        return 0
    if distance <= 5:
        return 3
    if distance <= 15:
        return 2
    if distance <= 25:
        return 1
    return 0


def _score_days_apart(days: float | None) -> int:
    if days is None:
        return 0
    if days <= 30:
        return 3
    if days <= 180:
        return 2
    if days <= 365:
        return 1
    return 0


def _score_timeline(row: Mapping[str, str]) -> tuple[int, str]:
    starts = [_date(_value(row, "start_date_a", "utility a start date")),
              _date(_value(row, "start_date_b", "utility b start date"))]
    ends = [_date(_value(row, "in_service_date_a", "utility a date", "in-service date a")),
            _date(_value(row, "in_service_date_b", "utility b date", "in-service date b"))]
    if not all(ends):
        return 0, "timeline overlap unavailable"

    # Only the documented DESC source gives a blank start an open-ended meaning.
    for index, suffix in enumerate(("a", "b")):
        raw_start = _value(row, f"start_date_{suffix}", f"utility {suffix} start date")
        if raw_start and starts[index] is None:
            return 0, "timeline dates inconsistent"
        if starts[index] is None:
            if _value(row, f"utility_{suffix}") == "Dominion Energy South Carolina":
                starts[index] = date.min
            else:
                return 0, "timeline overlap unavailable"
    if starts[0] > ends[0] or starts[1] > ends[1]:
        return 0, "timeline dates inconsistent"
    if max(starts) <= min(ends):
        return 3, "build windows overlap"
    return 0, "build windows do not overlap"


def _score_voltage(row: Mapping[str, str]) -> tuple[int, str]:
    voltages = [_voltage(_value(row, "voltage_a", "voltage_1_a", "max_voltage_a", "utility a voltage")),
                _voltage(_value(row, "voltage_b", "voltage_1_b", "max_voltage_b", "utility b voltage"))]
    if any(voltage is None for voltage in voltages):
        return 0, "voltage unavailable"
    difference = abs(voltages[0] - voltages[1])
    if difference == 0:
        return 3, "same voltage"
    if difference / max(voltages) <= 0.10:
        return 2, "similar voltage"
    return 1, "different known voltages"


def _score_type(row: Mapping[str, str]) -> tuple[int, str]:
    types = [_project_type(_value(row, "project_type_a", "type_a", "utility a project type")),
             _project_type(_value(row, "project_type_b", "type_b", "utility b project type"))]
    if not all(types):
        return 0, "project type unavailable"
    if types[0] == types[1]:
        return 3, f"matching {types[0].lower()} type"
    if "BOTH" in types:
        return 2, "one project supports both line and substation work"
    return 0, "different project types"


def rank_overlaps(rows: Iterable[Mapping[str, str]], projects: Iterable[Mapping[str, str]] = (), *, mode: str = "score") -> list[dict[str, str]]:
    """Return overlap rows with scores, ranked strongest first."""
    if mode not in {"score", "distance_first"}:
        raise ValueError("Ranking mode must be score or distance_first")
    project_lookup = {
        (row.get("utility", "").strip(), row.get("project_id", "").strip()): row
        for row in projects
        if row.get("utility", "").strip() and row.get("project_id", "").strip()
    }
    ranked = []
    for row in rows:
        enriched = dict(row)
        for suffix in ("a", "b"):
            project = project_lookup.get(_project_key(row, suffix))
            if project:
                for field, value in project.items():
                    enriched.setdefault(f"{field}_{suffix}", value)

        distance = _number(_value(enriched, "distance_miles", "distance miles"))
        days = _number(_value(enriched, "days_apart", "date_gap_days", "date gap days", "time_gap"))
        if days is None:
            service_dates = [
                _date(_value(enriched, "in_service_date_a", "utility a date", "in-service date a")),
                _date(_value(enriched, "in_service_date_b", "utility b date", "in-service date b")),
            ]
            if all(service_dates):
                days = abs((service_dates[0] - service_dates[1]).days)
        timeline_score, timeline_reason = _score_timeline(enriched)
        voltage_score, voltage_reason = _score_voltage(enriched)
        type_score, type_reason = _score_type(enriched)
        scores = {
            "distance_score": _score_distance(distance),
            "timeline_overlap_score": timeline_score,
            "days_apart_score": _score_days_apart(days),
            "power_voltage_score": voltage_score,
            "project_type_score": type_score,
        }
        enriched.update({key: str(value) for key, value in scores.items()})
        enriched["total_score"] = str(sum(scores.values()))
        enriched["ranking_reason"] = "; ".join(
            [
                f"distance {distance:.2f} miles" if distance is not None else "distance unavailable",
                timeline_reason,
                f"{days:.0f} days apart" if days is not None else "days apart unavailable",
                voltage_reason,
                type_reason,
            ]
        )
        enriched["_sort_distance"] = str(distance if distance is not None else math.inf)
        enriched["_sort_days"] = str(days if days is not None else math.inf)
        enriched["ranking_mode"] = mode
        ranked.append(enriched)

    def order(row):
        if mode == "distance_first":
            key = (-int(row["distance_score"]), -int(row["timeline_overlap_score"]),
                   float(row["_sort_days"]), -int(row["power_voltage_score"]),
                   -int(row["project_type_score"]), float(row["_sort_distance"]))
        else:
            key = (-int(row["total_score"]), float(row["_sort_distance"]))
        return (*key, _value(row, "utility_a"), _value(row, "project_id_a"),
                _value(row, "utility_b"), _value(row, "project_id_b"))

    ranked.sort(key=order)
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = str(rank)
        row.pop("_sort_distance", None)
        row.pop("_sort_days", None)
    return ranked


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rank Gridlock overlap opportunities.")
    parser.add_argument("overlaps", type=Path, help="overlap CSV to rank")
    parser.add_argument("-p", "--projects", type=Path, nargs="*", default=[], help="project CSVs for attribute enrichment")
    parser.add_argument("-o", "--output", type=Path, default=Path("ranked_overlaps.csv"))
    parser.add_argument("--mode", choices=["score", "distance_first"], default="score")
    args = parser.parse_args(argv)

    rows = rank_overlaps(_read_csv(args.overlaps), (row for path in args.projects for row in _read_csv(path)), mode=args.mode)
    if not rows:
        parser.error("overlap CSV contains no rows")
    fieldnames = list(rows[0])
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
