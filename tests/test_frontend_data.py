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


@pytest.mark.parametrize(
    "endpoints, method",
    [
        (dict(location_1="Sub A", lat_a="32", lon_a="-81"), "single_location"),
        (dict(location_1="Sub A", lat_a="32", lon_a="-81", location_2="Sub B"), "one_of_two_endpoints"),
        (dict(location_1="Sub A", location_2="Sub B", lat_b="32", lon_b="-81"), "one_of_two_endpoints"),
        (dict(location_1="Sub A", lat_a="32", lon_a="-81", location_2="Sub B", lat_b="33"), "one_of_two_endpoints"),
    ],
)
def test_one_located_endpoint_is_labeled_by_whether_a_second_was_named(endpoints, method):
    frame = pd.DataFrame([dict(project_id="1", project_name="Line", **endpoints)])
    row = _normalize_projects(frame, "A", "test.csv").iloc[0]
    assert (row.Latitude, row.Longitude) == (32, -81)
    assert row["Center Method"] == method


def test_real_two_substation_projects_with_one_failed_lookup_are_not_single_location():
    rows = load_demo_projects().set_index(["Utility", "Project ID"])
    for key in [(DESC, "05004 P"), (GEORGIA, "20464")]:
        assert rows.loc[key, "Center Method"] == "single_location"
    # Hooks and Yates Common were not found; the center is the other substation.
    for key, point in [((DESC, "6810 A"), 2), ((GEORGIA, "19601"), 1)]:
        row = rows.loc[key]
        assert row["Center Method"] == "one_of_two_endpoints"
        assert row.Latitude == row[f"Point {point} Latitude"]
        assert row.Confidence == "Low"


def test_vcs2_override_gives_the_vcs2_ward_line_its_midpoint():
    row = load_demo_projects().set_index(["Utility", "Project ID"]).loc[(DESC, "06810 F")]
    assert (row["Point 1 Name"], row["Point 2 Name"]) == ("VCS2", "Ward")
    assert row["Center Method"] == "endpoint_midpoint"
    assert row.Latitude == pytest.approx((34.2903782 + row["Point 2 Latitude"]) / 2)
    assert row.Confidence == "High"


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
