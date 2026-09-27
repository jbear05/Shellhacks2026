import pandas as pd
import pytest

from frontend.analysis import calculate_overlaps
from frontend.project_data import DESC, GEORGIA, load_demo_projects
from frontend.workspace import export_bundle, restore_bundle, apply_location_review
from frontend.data_loader import ProjectLoadError, _normalize_projects, prepare_projects


def test_snapshot_restores_reviews_settings_and_identical_ranked_results():
    projects = load_demo_projects()
    projects.loc[projects["Project ID"] == "6810 A", "Location Status"] = "Excluded"
    settings = dict(format_version=1, utility_a=DESC, utility_b=GEORGIA, threshold_miles=25, include_low=True, ranking_mode="distance_first")
    results = calculate_overlaps(projects, DESC, GEORGIA)
    restored, loaded_settings = restore_bundle(export_bundle(projects, results, settings))
    assert loaded_settings == settings
    actual = calculate_overlaps(restored, DESC, GEORGIA)
    pd.testing.assert_frame_equal(actual, results)


def test_invalid_snapshot_has_a_readable_error():
    with pytest.raises(ProjectLoadError, match="restore snapshot"):
        restore_bundle(b"not a zip")


def test_coordinate_edit_resets_confidence_and_preserves_original_evidence():
    original = load_demo_projects().iloc[[0]].copy()
    edited = original.copy()
    edited.loc[0, "Point 1 Latitude"] += 0.1
    reviewed, ignored = apply_location_review(original, edited)
    assert ignored == []
    assert reviewed.loc[0, "Confidence"] == "Low"
    assert reviewed.loc[0, "Location Source"] == "User review"
    assert reviewed.loc[0, "Original Point 1 Latitude"] == original.loc[0, "Point 1 Latitude"]


def test_center_edit_on_an_endpoint_project_is_ignored_and_keeps_its_evidence():
    projects = load_demo_projects()
    row = projects.index[projects["Project ID"] == "06810 F"][0]
    edited = projects.copy()
    edited.loc[row, "Latitude"] += 0.5
    reviewed, ignored = apply_location_review(projects, edited)
    assert ignored == [f"{DESC} · 06810 F"]
    fields = ["Latitude", "Center Method", "Confidence", "Location Source", "Verification Notes"]
    assert reviewed.loc[row, fields].tolist() == projects.loc[row, fields].tolist()
    assert reviewed.loc[row, "Confidence"] == "High"
    assert "Original Latitude" not in reviewed


def test_center_typed_for_a_center_only_project_without_one_is_kept():
    frame = pd.DataFrame([dict(project_id="1", project_name="Located", center_lat="32", center_lon="-81"),
                          dict(project_id="2", project_name="Missing", center_lat="", center_lon="")])
    projects = _normalize_projects(frame, "A", "test.csv")
    assert projects.loc[1, "Center Method"] == "unavailable"
    edited = projects.copy()
    edited.loc[1, ["Latitude", "Longitude"]] = [33.0, -82.0]
    reviewed, ignored = apply_location_review(projects, edited)
    assert ignored == []
    assert reviewed.loc[1, ["Latitude", "Longitude", "Center Method", "Location Source"]].tolist() == [33.0, -82.0, "provided_center", "User review"]
    assert prepare_projects(reviewed).loc[1, "Center Method"] == "provided_center"
