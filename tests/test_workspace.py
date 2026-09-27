import pandas as pd
import pytest

from frontend.analysis import calculate_overlaps
from frontend.project_data import DESC, GEORGIA, load_demo_projects
from frontend.workspace import export_bundle, restore_bundle, apply_location_review
from frontend.data_loader import ProjectLoadError


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
    reviewed = apply_location_review(original, edited)
    assert reviewed.loc[0, "Confidence"] == "Low"
    assert reviewed.loc[0, "Location Source"] == "User review"
    assert reviewed.loc[0, "Original Point 1 Latitude"] == original.loc[0, "Point 1 Latitude"]
