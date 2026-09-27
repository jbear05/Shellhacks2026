"""Offline adapters for the committed public plans and reviewed location evidence."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from frontend.data_loader import _normalize_projects, valid_point

ROOT = Path(__file__).resolve().parents[1]
DESC = "Dominion Energy South Carolina"
GEORGIA = "Georgia Power"
SOURCE_FILES = {
    DESC: "Sperry-Tech-Challenge/Project Listings/Dominion Energy/2024-2028-2million-and-above-project-descriptions.pdf",
    GEORGIA: "Sperry-Tech-Challenge/Project Listings/Georgia Power/2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf",
}


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def attach_locations(frame: pd.DataFrame, prefix: str, source_file: str) -> pd.DataFrame:
    """Join saved evidence by utility/ID; use only location_1 and location_2."""
    locations = read_csv(ROOT / "data" / "processed" / f"{prefix}_project_locations.csv")
    lookup = {(u, p): group for (u, p), group in locations.groupby(["utility", "project_id"])}
    rows = []
    for project in frame.to_dict("records"):
        row = dict(project)
        points = lookup.get((str(row["utility"]), str(row["project_id"])))
        confidence = []
        sources = []
        notes = []
        if points is not None:
            for number in (1, 2):
                endpoint = points[points.location_role == f"location_{number}"]
                if endpoint.empty:
                    continue
                point = endpoint.iloc[0]
                row[f"location_{number}"] = point.target_location
                row[f"location_{number}_lat"] = point.latitude
                row[f"location_{number}_lon"] = point.longitude
                for field in ("confidence", "source", "osm_type", "osm_id", "reasons"):
                    row[f"Point {number} {field.replace('_', ' ').title()}"] = point[field]
                confidence.append(point.confidence.title() if valid_point(point.latitude, point.longitude) else "Low")
                sources.append(point.source)
                notes.append(f"{point.target_location}: {point.reasons}")
            row.setdefault("project_type", points.iloc[0].project_type)
            if not row.get("voltage_1"):
                volts = points.iloc[0].expected_voltages.split(";")
                row["voltage_1"] = volts[0]
                row["voltage_2"] = volts[1] if len(volts) > 1 else ""
        row["confidence"] = min(confidence, key=lambda value: {"Low": 0, "Medium": 1, "High": 2}.get(value, 0)) if confidence else "Low"
        row["location_source"] = "; ".join(dict.fromkeys(filter(None, sources)))
        row["verification_notes"] = " | ".join(notes)
        row["center_method"] = "unavailable"
        row["source_file"] = source_file
        row["source_pages"] = "; ".join(str(row[field]) for field in ("table_page", "detail_page") if row.get(field))
        # The DESC parser does not emit a page column; retain the source ID for lookup.
        rows.append(row)
    return _normalize_projects(pd.DataFrame(rows), "", source_file)


def load_demo_projects() -> pd.DataFrame:
    desc = read_csv(ROOT / "data" / "processed" / "dominion_projects.csv")
    georgia = read_csv(ROOT / "data" / "processed" / "georgia_power_projects.csv")
    georgia = georgia[georgia.utility == GEORGIA]
    return pd.concat([
        attach_locations(desc, "desc", SOURCE_FILES[DESC]),
        attach_locations(georgia, "georgia_power", SOURCE_FILES[GEORGIA]),
    ], ignore_index=True).fillna("")
