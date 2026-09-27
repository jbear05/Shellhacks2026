"""Small session and export helpers for the five-page Streamlit workflow."""
from __future__ import annotations

from io import BytesIO
import json
from zipfile import ZipFile

import pandas as pd

from frontend.analysis import calculate_overlaps
from frontend.data_loader import ProjectLoadError, _normalize_projects, prepare_projects


def analyze_state(state):
    return calculate_overlaps(
        state["projects"], state["utility_a"], state["utility_b"],
        float(state.get("threshold_miles", 25)), bool(state.get("include_low", True)),
        state.get("ranking_mode", "distance_first"),
    )


def settings_from_state(state):
    return {"format_version": 1, "utility_a": state["utility_a"], "utility_b": state["utility_b"],
            "threshold_miles": float(state.get("threshold_miles", 25)),
            "include_low": bool(state.get("include_low", True)),
            "ranking_mode": state.get("ranking_mode", "distance_first")}


def export_bundle(projects, results, settings):
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr("projects.csv", projects.to_csv(index=False))
        archive.writestr("ranked_overlaps.csv", results.to_csv(index=False))
        archive.writestr("settings.json", json.dumps(settings, indent=2))
        archive.writestr("README.txt", "Gridlock analysis snapshot\nUpload this ZIP on Project Setup to restore projects, reviews and settings.\nResults are recalculated from saved endpoints. Connection lines join project centers; they are not actual transmission routes.\nSource plans describe historical planning windows, not current construction status.\n")
    return output.getvalue()


def restore_bundle(content):
    try:
        with ZipFile(BytesIO(content)) as archive:
            if any(archive.getinfo(name).file_size > 20_000_000 for name in ("projects.csv", "settings.json")):
                raise ValueError("Snapshot tables are too large")
            settings = json.loads(archive.read("settings.json"))
            if settings.get("format_version") != 1:
                raise ValueError("Unsupported snapshot version")
            if settings.get("ranking_mode") not in {"score", "distance_first"} or type(settings.get("include_low")) is not bool:
                raise ValueError("Invalid analysis settings")
            projects = _normalize_projects(pd.read_csv(BytesIO(archive.read("projects.csv")), dtype=str, keep_default_na=False), "", "Restored snapshot")
            if projects is None:
                raise ValueError("No project table")
            for key in ("utility_a", "utility_b"):
                if settings.get(key) not in projects.Utility.values:
                    raise ValueError("Snapshot utility does not match its projects")
            if not 1 <= float(settings["threshold_miles"]) <= 100:
                raise ValueError("Threshold must be between 1 and 100 miles")
            analyze_state({**settings, "projects": projects})
            return projects, settings
    except Exception as error:
        raise ProjectLoadError(f"Could not restore snapshot: {error}") from error


def apply_location_review(original, edited):
    """Mark coordinate edits as user evidence and retain original point values."""
    result = edited.copy().astype(object)
    for index in result.index:
        changed = False
        for column in ("Point 1 Latitude", "Point 1 Longitude", "Point 2 Latitude", "Point 2 Longitude", "Latitude", "Longitude"):
            old, new = original.at[index, column], result.at[index, column]
            if (pd.isna(old) and pd.isna(new)) or str(old) == str(new):
                continue
            changed = True
            result.at[index, f"Original {column}"] = original.at[index, f"Original {column}"] if f"Original {column}" in original else old
        if changed:
            result.at[index, "Location Source"] = "User review"
            result.at[index, "Confidence"] = "Low"
            result.at[index, "Location Status"] = "Candidate"
            result.at[index, "Verification Notes"] = "Coordinates edited by user; confidence reset for review. " + str(result.at[index, "Verification Notes"])
    return prepare_projects(result)
