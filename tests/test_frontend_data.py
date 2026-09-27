"""Real-data and file-boundary checks, with no Streamlit server or network."""
from io import BytesIO

import pandas as pd
import pytest

from frontend.data_loader import ProjectLoadError, _normalize_projects, load_uploaded_projects, prepare_projects
from frontend.project_data import DESC, GEORGIA, load_demo_projects


def upload(text, name="projects.csv"):
    file = BytesIO(text.encode())
    file.name = name
    return file


def test_csv_preserves_id_ownership_and_duplicate_ids_across_utilities():
    a = upload("project_id,project_name,utility,lat,lon\n09662,First,Actual A,32,-81")
    b = upload("project_id,project_name,utility,lat,lon\n09662,Second,Actual B,33,-82")
    rows = load_uploaded_projects([a], [b], "Wrong A", "Wrong B")
    assert rows["Project ID"].tolist() == ["09662", "09662"]
    assert rows.Utility.tolist() == ["Actual A", "Actual B"]


def test_duplicate_key_is_an_error_instead_of_silent_data_loss():
    file = upload("project_id,project_name\n001,One\n001,Two")
    with pytest.raises(ProjectLoadError, match="Duplicate"):
        load_uploaded_projects([file], [], "Utility A", "Utility B")


def test_partial_endpoints_do_not_create_a_point_from_different_locations():
    frame = pd.DataFrame([dict(project_id="1", project_name="Partial", lat_a="32", lon_b="-81")])
    result = _normalize_projects(frame, "Utility A", "test.csv")
    assert pd.isna(result.iloc[0].Latitude)
    assert result.iloc[0]["Center Method"] == "unavailable"


def test_edits_recalculate_centers_and_deleting_endpoints_clears_stale_center():
    frame = pd.DataFrame([dict(project_id="1", project_name="Line", lat_a="32", lon_a="-81", lat_b="34", lon_b="-83")])
    result = _normalize_projects(frame, "A", "test.csv")
    assert result.iloc[0].Latitude == 33
    result.loc[0, "Point 2 Latitude"] = 36
    assert prepare_projects(result).iloc[0].Latitude == 34
    result[["Point 1 Latitude", "Point 1 Longitude", "Point 2 Latitude", "Point 2 Longitude"]] = float("nan")
    assert pd.isna(prepare_projects(result).iloc[0].Latitude)


def test_real_demo_joins_dates_endpoints_and_source_evidence():
    rows = load_demo_projects()
    assert rows.groupby("Utility").size().to_dict() == {DESC: 44, GEORGIA: 138}
    assert "09661" in rows["Project ID"].values
    pair = rows[(rows.Utility == DESC) & (rows["Project ID"] == "06367 D-G")].iloc[0]
    assert pair["In-Service Date"] == "2025-12-31"
    assert pair["Center Method"] == "endpoint_midpoint"
    assert pair.Latitude == pytest.approx((pair["Point 1 Latitude"] + pair["Point 2 Latitude"]) / 2)
    assert "Manual override" in pair["Location Source"]
    assert "OSM" in pair["Verification Notes"]
    assert "Sperry-Tech-Challenge" in pair["Source File"]


def test_synthetic_coordinate_aliases_and_invalid_dates_are_visible():
    frame = pd.DataFrame([dict(project_id="1", project_name="Test", center_lat="32", center_lon="-81", start_date="2027-01-01", in_service_date="2026-01-01")])
    row = _normalize_projects(frame, "A", "test.csv").iloc[0]
    assert row.Latitude == 32
    assert "after" in row["Data Warnings"]
