from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


class ProjectLoadError(Exception):
    """Raised when an uploaded project file cannot be imported."""


CANONICAL_COLUMNS = [
    "Project ID",
    "Project Name",
    "Utility",
    "Project Type",
    "County / Region",
    "Start Date",
    "In-Service Date",
    "Voltage 1",
    "Voltage 2",
    "Latitude",
    "Longitude",
    "Point 1 Name",
    "Point 1 Latitude",
    "Point 1 Longitude",
    "Point 2 Name",
    "Point 2 Latitude",
    "Point 2 Longitude",
    "Match Status",
    "Confidence",
    "Location Status",
    "Location Source",
    "Verification Notes",
    "Center Method",
    "Source Pages",
    "Description",
    "Data Warnings",
]

COLUMN_ALIASES = {
    "project_id": "Project ID",
    "id": "Project ID",
    "project_name": "Project Name",
    "name": "Project Name",
    "utility": "Utility",
    "operator": "Utility",
    "project_type": "Project Type",
    "type": "Project Type",
    "county_region": "County / Region",
    "county": "County / Region",
    "region": "County / Region",
    "state": "County / Region",
    "in_service_date": "In-Service Date",
    "inservice_date": "In-Service Date",
    "start_date": "Start Date",
    "voltage_1": "Voltage 1",
    "voltage_2": "Voltage 2",
    "latitude": "Latitude",
    "lat": "Latitude",
    "longitude": "Longitude",
    "lon": "Longitude",
    "lng": "Longitude",
    "name_a": "Point 1 Name",
    "lat_a": "Point 1 Latitude",
    "lon_a": "Point 1 Longitude",
    "name_b": "Point 2 Name",
    "lat_b": "Point 2 Latitude",
    "lon_b": "Point 2 Longitude",
    "lat_center": "Latitude",
    "lon_center": "Longitude",
    "match_status": "Match Status",
    "confidence": "Confidence",
    "location_status": "Location Status",
    "location_source": "Location Source",
    "verification_notes": "Verification Notes",
    "centroid_latitude": "Latitude",
    "centroid_longitude": "Longitude",
    "center_lat": "Latitude",
    "center_lon": "Longitude",
    "center_latitude": "Latitude",
    "center_longitude": "Longitude",
    "overall_confidence": "Confidence",
    "center_method": "Center Method",
    "source_file": "Source File",
    "source_pages": "Source Pages",
    "description": "Description",
    "data_warnings": "Data Warnings",
}
for _point in (1, 2):
    COLUMN_ALIASES.update({
        f"location_{_point}": f"Point {_point} Name",
        f"location_{_point}_lat": f"Point {_point} Latitude",
        f"location_{_point}_lon": f"Point {_point} Longitude",
        f"point_{_point}_name": f"Point {_point} Name",
        f"point_{_point}_latitude": f"Point {_point} Latitude",
        f"point_{_point}_longitude": f"Point {_point} Longitude",
    })


def _normalized_name(value: Any) -> str:
    return "_".join(
        str(value).strip().lower().replace("/", " ").replace("-", " ").split()
    )


def _read_file(uploaded_file: Any) -> list[tuple[str, pd.DataFrame]]:
    filename = Path(uploaded_file.name).name
    suffix = Path(filename).suffix.lower()

    try:
        uploaded_file.seek(0)
        if suffix == ".csv":
            return [(filename, pd.read_csv(uploaded_file, dtype=str, keep_default_na=False))]
        if suffix in {".xlsx", ".xlsm"}:
            sheets = pd.read_excel(uploaded_file, sheet_name=None, dtype=str, keep_default_na=False)
            return [
                (f"{filename} / {sheet_name}", frame)
                for sheet_name, frame in sheets.items()
            ]
    except Exception as error:
        raise ProjectLoadError(f"Could not read {filename}: {error}") from error

    if suffix == ".pdf":
        raise ProjectLoadError(
            f"{filename} is a PDF. PDF extraction is not implemented yet; "
            "please upload a CSV or XLSX project table."
        )

    raise ProjectLoadError(
        f"{filename} has an unsupported file type. Upload CSV or XLSX files."
    )


def _normalize_projects(
    frame: pd.DataFrame,
    utility_name: str,
    source_name: str,
) -> pd.DataFrame | None:
    if frame.empty:
        return None

    normalized_columns = {
        _normalized_name(column): column for column in frame.columns
    }
    if not {"project_name", "name"}.intersection(normalized_columns):
        return None

    # Overlap summary sheets have project_name_a but no project_name and are skipped.
    renamed = {}
    for normalized, original in normalized_columns.items():
        canonical = COLUMN_ALIASES.get(normalized)
        if canonical and canonical not in renamed:
            renamed[original] = canonical

    projects = frame.rename(columns=renamed).copy()
    projects = projects.loc[:, ~projects.columns.duplicated()]

    if "Project Name" not in projects.columns:
        return None

    projects["Project Name"] = projects["Project Name"].fillna("").astype(str).str.strip()
    projects = projects[projects["Project Name"] != ""].copy()
    if projects.empty:
        return None

    # A selected label fills missing ownership; it never relabels another utility.
    if "Utility" not in projects:
        projects["Utility"] = utility_name
    projects["Utility"] = projects["Utility"].fillna("").astype(str).str.strip().replace("", utility_name)

    for column in CANONICAL_COLUMNS:
        if column not in projects.columns:
            projects[column] = ""

    numeric_columns = [
        "Latitude",
        "Longitude",
        "Point 1 Latitude",
        "Point 1 Longitude",
        "Point 2 Latitude",
        "Point 2 Longitude",
    ]
    for column in numeric_columns:
        projects[column] = pd.to_numeric(projects[column], errors="coerce")

    if "Source File" not in projects:
        projects["Source File"] = source_name
    else:
        projects["Source File"] = projects["Source File"].fillna("").replace("", source_name)
    return prepare_projects(projects)


def valid_point(latitude: Any, longitude: Any) -> bool:
    try:
        return -90 <= float(latitude) <= 90 and -180 <= float(longitude) <= 180
    except (TypeError, ValueError):
        return False


def prepare_projects(projects: pd.DataFrame) -> pd.DataFrame:
    """Recompute centers after imports/edits, keeping incomplete points together."""
    result = projects.copy().fillna("")
    for column in CANONICAL_COLUMNS:
        if column not in result:
            result[column] = ""
    for column in ("Project ID", "Utility"):
        result[column] = result[column].astype(str).str.strip()
    if (result[["Project ID", "Utility"]] == "").any().any():
        raise ProjectLoadError("Every project needs a Project ID and Utility.")
    if result.duplicated(["Utility", "Project ID"]).any():
        raise ProjectLoadError("Duplicate (Utility, Project ID). Upload one project table per utility.")
    # Object columns allow editable numeric coordinates and empty values in pandas 3.
    result = result.astype(object)
    for index, row in result.iterrows():
        warnings = []
        points = []
        named_endpoints = 0
        for number in (1, 2):
            lat, lon = row[f"Point {number} Latitude"], row[f"Point {number} Longitude"]
            named_endpoints += bool(str(row[f"Point {number} Name"]).strip() or str(lat).strip() or str(lon).strip())
            if valid_point(lat, lon):
                points.append((float(lat), float(lon)))
            elif str(lat).strip() or str(lon).strip():
                warnings.append(f"Point {number} incomplete or outside coordinate bounds")
        if points:
            result.at[index, "Latitude"] = sum(p[0] for p in points) / len(points)
            result.at[index, "Longitude"] = sum(p[1] for p in points) / len(points)
            if len(points) == 2:
                result.at[index, "Center Method"] = "endpoint_midpoint"
            else:
                # A named endpoint without usable coordinates means the true midpoint is unknown.
                result.at[index, "Center Method"] = "one_of_two_endpoints" if named_endpoints == 2 else "single_location"
        elif named_endpoints or row["Center Method"] in {"endpoint_midpoint", "single_location", "one_of_two_endpoints", "unavailable"}:
            result.at[index, "Latitude"] = float("nan")
            result.at[index, "Longitude"] = float("nan")
            result.at[index, "Center Method"] = "unavailable"
        elif valid_point(row["Latitude"], row["Longitude"]):
            result.at[index, "Center Method"] = row["Center Method"] or "provided_center"
        else:
            result.at[index, "Latitude"] = float("nan")
            result.at[index, "Longitude"] = float("nan")
            result.at[index, "Center Method"] = "unavailable"
        located = valid_point(result.at[index, "Latitude"], result.at[index, "Longitude"])
        if not located:
            warnings.append("No usable project center")
        confidence = str(row["Confidence"]).strip().title()
        result.at[index, "Confidence"] = confidence if confidence in {"High", "Medium", "Low"} else "Low"
        result.at[index, "Location Status"] = row["Location Status"] or ("Candidate" if located else "Missing")
        result.at[index, "Match Status"] = row["Match Status"] or "Unmatched"
        dates = {}
        for field in ("Start Date", "In-Service Date"):
            value = str(row[field]).strip()
            parsed = pd.to_datetime(value, errors="coerce") if value else pd.NaT
            if value and pd.isna(parsed):
                warnings.append(f"Invalid {field}")
            dates[field] = parsed
        if pd.notna(dates["Start Date"]) and pd.notna(dates["In-Service Date"]) and dates["Start Date"] > dates["In-Service Date"]:
            warnings.append("Start Date is after In-Service Date")
        result.at[index, "Data Warnings"] = "; ".join(warnings)
    for column in ["Latitude", "Longitude", "Point 1 Latitude", "Point 1 Longitude", "Point 2 Latitude", "Point 2 Longitude"]:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    return result


def load_uploaded_projects(
    files_a: list[Any],
    files_b: list[Any],
    utility_a: str,
    utility_b: str,
) -> pd.DataFrame:
    loaded_frames = []
    errors = []

    for files, utility_name in ((files_a, utility_a), (files_b, utility_b)):
        for uploaded_file in files:
            try:
                sheets = _read_file(uploaded_file)
                valid_sheet_found = False
                for source_name, frame in sheets:
                    projects = _normalize_projects(frame, utility_name, source_name)
                    if projects is not None:
                        loaded_frames.append(projects)
                        valid_sheet_found = True
                if not valid_sheet_found:
                    errors.append(
                        f"{uploaded_file.name}: no sheet contained a Project Name column."
                    )
            except ProjectLoadError as error:
                errors.append(str(error))

    if errors:
        raise ProjectLoadError("\n".join(errors))

    if not loaded_frames:
        return pd.DataFrame(columns=CANONICAL_COLUMNS + ["Source File"])

    projects = pd.concat(loaded_frames, ignore_index=True, sort=False)
    return prepare_projects(projects)
