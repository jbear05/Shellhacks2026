"""Pure overlap analysis shared by results, maps, exports and regression tests."""
from __future__ import annotations

import math

import pandas as pd

from frontend.data_loader import prepare_projects, valid_point
from ranking import rank_overlaps

PAIR_FIELDS = {
    "utility": "Utility", "project_id": "Project ID", "project_name": "Project Name",
    "project_type": "Project Type", "start_date": "Start Date", "in_service_date": "In-Service Date",
    "voltage": "Voltage 1", "confidence": "Confidence", "center_method": "Center Method",
    "latitude": "Latitude", "longitude": "Longitude", "source_file": "Source File",
    "source_pages": "Source Pages", "verification_notes": "Verification Notes",
    "data_warnings": "Data Warnings",
}
PAIR_COLUMNS = [f"{name}_{suffix}" for suffix in ("a", "b") for name in PAIR_FIELDS]
RESULT_COLUMNS = ["rank", "overlap_id", "distance_miles", "days_apart", "timeline_overlap", *PAIR_COLUMNS,
                  "distance_score", "timeline_overlap_score", "days_apart_score", "power_voltage_score",
                  "project_type_score", "total_score", "ranking_reason", "ranking_mode"]


def haversine_miles(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, map(float, (lat1, lon1, lat2, lon2)))
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 3958.8 * math.asin(math.sqrt(min(1.0, max(0.0, a))))


def eligible_projects(projects: pd.DataFrame, include_low: bool = True) -> pd.DataFrame:
    rows = prepare_projects(projects)
    usable = rows.apply(lambda row: valid_point(row.Latitude, row.Longitude), axis=1)
    excluded = rows[["Location Status", "Match Status"]].apply(lambda col: col.astype(str).str.casefold().eq("excluded")).any(axis=1)
    confidence = rows.Confidence.isin(["High", "Medium"]) if not include_low else True
    return rows[usable & ~excluded & confidence].copy()


def calculate_overlaps(projects: pd.DataFrame, utility_a: str, utility_b: str,
                       threshold: float = 25, include_low: bool = True,
                       ranking_mode: str = "distance_first") -> pd.DataFrame:
    if not utility_a or not utility_b or utility_a == utility_b:
        raise ValueError("Choose two distinct utilities.")
    if not math.isfinite(threshold) or threshold <= 0:
        raise ValueError("Distance threshold must be a positive finite number.")
    eligible = eligible_projects(projects, include_low)
    a_rows = eligible[eligible.Utility == utility_a].to_dict("records")
    b_rows = eligible[eligible.Utility == utility_b].to_dict("records")
    pairs = []
    for a in a_rows:
        for b in b_rows:
            distance = haversine_miles(a["Latitude"], a["Longitude"], b["Latitude"], b["Longitude"])
            # Test the unrounded distance; display rounding must not admit >25 miles.
            if distance > threshold:
                continue
            pair = {"distance_miles": distance}
            for suffix, project in (("a", a), ("b", b)):
                for field, column in PAIR_FIELDS.items():
                    value = project.get(column, "")
                    pair[f"{field}_{suffix}"] = "" if pd.isna(value) else str(value)
                for field in ("start_date", "in_service_date"):
                    value = pair[f"{field}_{suffix}"]
                    parsed = pd.to_datetime(value, errors="coerce") if value else pd.NaT
                    if pd.notna(parsed):
                        pair[f"{field}_{suffix}"] = parsed.date().isoformat()
            dates = [pd.to_datetime(pair[f"in_service_date_{s}"], errors="coerce") for s in ("a", "b")]
            pair["days_apart"] = abs((dates[0] - dates[1]).days) if all(pd.notna(d) for d in dates) else ""
            pairs.append(pair)
    ranked = rank_overlaps(pairs, mode=ranking_mode)
    for row in ranked:
        reason = row["ranking_reason"]
        row["timeline_overlap"] = "Yes" if "build windows overlap" in reason else "No" if "build windows do not overlap" in reason else "Unknown"
        row["overlap_id"] = f"{row['utility_a']}:{row['project_id_a']} | {row['utility_b']}:{row['project_id_b']}"
        row["rank"] = int(row["rank"])
    return pd.DataFrame(ranked, columns=RESULT_COLUMNS)
