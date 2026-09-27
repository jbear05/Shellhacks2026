"""Ranking helpers for the Streamlit overlap results page."""

from __future__ import annotations

from datetime import date
import math
from collections.abc import Mapping


def _number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _date(value):
    if value is None or str(value).strip() in {"", "NaT", "nan"}:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _voltage(value):
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip().lower().replace(" ", "")
    is_kv = text.endswith("kv")
    if is_kv:
        text = text[:-2]
    number = _number(text)
    if number is None:
        return None
    return number * 1000 if is_kv or number < 1000 else number


def _project_type(value):
    text = str(value or "").strip().upper().replace(" ", "_")
    if text in {"LINE", "TRANSMISSION_LINE", "MULTI_LINE"}:
        return "LINE"
    if text in {"SUBSTATION", "STATION"}:
        return "SUBSTATION"
    if text in {"BOTH", "MULTI_SITE"}:
        return "BOTH"
    return ""


def _score_distance(distance):
    if distance is None:
        return 0
    if distance <= 5:
        return 3
    if distance <= 15:
        return 2
    if distance <= 25:
        return 1
    return 0


def _score_days(days):
    if days is None:
        return 0
    if days <= 30:
        return 3
    if days <= 180:
        return 2
    if days <= 365:
        return 1
    return 0


def _timeline_score(row):
    starts = [_date(row.get("start_date_a")), _date(row.get("start_date_b"))]
    ends = [_date(row.get("in_service_date_a")), _date(row.get("in_service_date_b"))]
    if not all(ends):
        return 0, "timeline overlap unavailable"
    starts = [value or date.min for value in starts]
    if any(start > end for start, end in zip(starts, ends)):
        return 0, "timeline dates inconsistent"
    if max(starts) <= min(ends):
        return 3, "build windows overlap"
    return 0, "build windows do not overlap"


def _voltage_score(row):
    voltages = [_voltage(row.get("voltage_a")), _voltage(row.get("voltage_b"))]
    if any(value is None for value in voltages):
        return 0, "voltage unavailable"
    if voltages[0] == voltages[1]:
        return 3, "same voltage"
    if abs(voltages[0] - voltages[1]) / max(voltages) <= 0.10:
        return 2, "similar voltage"
    return 1, "different known voltages"


def _type_score(row):
    types = [_project_type(row.get("project_type_a")), _project_type(row.get("project_type_b"))]
    if not all(types):
        return 0, "project type unavailable"
    if types[0] == types[1]:
        return 3, f"matching {types[0].lower()} type"
    if "BOTH" in types:
        return 2, "one project supports both line and substation work"
    return 0, "different project types"


def rank_overlaps(rows: list[Mapping[str, object]]) -> list[dict[str, object]]:
    """Add five-category scores and return rows ordered strongest first."""
    ranked = []
    for source_row in rows:
        row = dict(source_row)
        distance = _number(row.get("distance_miles"))
        end_dates = [_date(row.get("in_service_date_a")), _date(row.get("in_service_date_b"))]
        days = _number(row.get("days_apart"))
        if days is None and all(end_dates):
            days = abs((end_dates[0] - end_dates[1]).days)
        timeline_score, timeline_reason = _timeline_score(row)
        voltage_score, voltage_reason = _voltage_score(row)
        type_score, type_reason = _type_score(row)
        scores = {
            "distance_score": _score_distance(distance),
            "timeline_overlap_score": timeline_score,
            "days_apart_score": _score_days(days),
            "power_voltage_score": voltage_score,
            "project_type_score": type_score,
        }
        row.update(scores)
        row["total_score"] = sum(scores.values())
        row["ranking_reason"] = "; ".join([
            f"distance {distance:.2f} miles" if distance is not None else "distance unavailable",
            timeline_reason,
            f"{days:.0f} days apart" if days is not None else "days apart unavailable",
            voltage_reason,
            type_reason,
        ])
        row["_sort_distance"] = distance if distance is not None else math.inf
        ranked.append(row)

    ranked.sort(key=lambda row: (-row["total_score"], row["_sort_distance"]))
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank
        row.pop("_sort_distance", None)
    return ranked
