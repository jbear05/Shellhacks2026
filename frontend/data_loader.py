from __future__ import annotations

from io import BytesIO, StringIO
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
    "In-Service Date",
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
}


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
            return [(filename, pd.read_csv(uploaded_file))]
        if suffix in {".xlsx", ".xlsm"}:
            sheets = pd.read_excel(uploaded_file, sheet_name=None)
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
    if "project_name" not in normalized_columns:
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

    # Each uploader is assigned to one selected utility. This keeps downstream
    # matching consistent even when a source file uses an internal label.
    projects["Utility"] = utility_name

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

    # Use the midpoint when a source provides endpoints but no center coordinates.
    endpoint_latitudes = projects[["Point 1 Latitude", "Point 2 Latitude"]]
    endpoint_longitudes = projects[["Point 1 Longitude", "Point 2 Longitude"]]
    projects["Latitude"] = projects["Latitude"].fillna(endpoint_latitudes.mean(axis=1))
    projects["Longitude"] = projects["Longitude"].fillna(endpoint_longitudes.mean(axis=1))

    projects["Source File"] = source_name
    return projects


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
    if "Project ID" in projects.columns:
        projects = projects.drop_duplicates(subset=["Project ID"], keep="first")
    return projects
