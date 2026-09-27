"""The Geolocator's tile search and manual overrides. The network calls are replaced, so
nothing here sends a request. Importing the module reads the committed geocode cache."""

import csv

import pytest

import gridlock_desc_locator as locator

GEORGIA = "Georgia Power"
DESC = "Dominion Energy South Carolina"


def project(utility=GEORGIA, project_id="20793"):
    return {
        "number": 1,
        "project_id": project_id,
        "utility": utility,
        "state": "Georgia",
        "project_name": "EVANS PRIMARY - THURMOND DAM (USA) #5 115KV REBUILD",
        "project_type": "LINE",
        "voltages": ["115000"],
        "locations": ["EVANS PRIMARY", "THURMOND DAM"],
    }


def override(**fields):
    row = {
        "utility": GEORGIA,
        "project_id": "",
        "target_location": "Evans Primary",
        "latitude": "33.5",
        "longitude": "-82.1",
        "matched_name": "Evans Primary Substation",
        "osm_type": "way",
        "osm_id": "123",
        "source": "OSM way 123",
        "note": "Nominatim finds Evans County",
    }
    return {**row, **fields}


def write_overrides(path, rows, fields=locator.OVERRIDE_FIELDS):
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def substation(osm_id, lat, lon, osm_type="node"):
    if osm_type == "node":
        return {"type": "node", "id": osm_id, "lat": lat, "lon": lon, "tags": {}}
    return {"type": osm_type, "id": osm_id, "center": {"lat": lat, "lon": lon}, "tags": {}}


def test_a_point_mid_tile_needs_one_tile():
    assert locator.tiles_near(32.5, -80.5, 15.5) == [(32, -81)]


def test_a_point_near_a_corner_needs_four_tiles():
    assert sorted(locator.tiles_near(32.95, -80.05, 15.5)) == [(32, -81), (32, -80), (33, -81), (33, -80)]


def test_nearby_substations_come_from_every_touched_tile(monkeypatch):
    tiles = {
        (32, -81): [substation(1, 32.95, -80.10), substation(2, 32.20, -80.90)],  # 3 miles; 56 miles
        (32, -80): [substation(3, 32.95, -79.95, "way")],  # 6 miles
        (33, -81): [substation(3, 32.95, -79.95, "way")],  # on the edge, returned by both tiles
        (33, -80): [substation(3, 32.95, -79.95, "node")],  # same id, but a node
    }
    monkeypatch.setattr(locator, "fetch_substation_tile", lambda south, west: tiles[(south, west)])
    found = locator.search_nearby_substations(32.95, -80.05)
    assert sorted((element["type"], element["id"]) for element in found) == [("node", 1), ("node", 3), ("way", 3)]


@pytest.fixture
def empty_cache(monkeypatch):
    cache = {}
    monkeypatch.setattr(locator, "CACHE", cache)
    monkeypatch.setattr(locator, "save_cache", lambda cache: None)
    monkeypatch.setattr(locator, "FAILED_TILES", set())
    return cache


def test_a_tile_that_fails_is_fetched_as_quarters(monkeypatch, empty_cache):
    requested = []

    def download(south, west, size):
        requested.append((south, west, size))
        return None if size == 1 else [substation(len(requested), south, west)]

    monkeypatch.setattr(locator, "download_substations", download)
    assert len(locator.fetch_substation_tile(32, -81)) == 4
    assert requested == [(32, -81, 1), (32, -81, 0.5), (32, -80.5, 0.5), (32.5, -81, 0.5), (32.5, -80.5, 0.5)]
    assert sorted(empty_cache) == [f"overpass-tile::{corner},0.5" for corner in ("32,-80.5", "32,-81", "32.5,-80.5", "32.5,-81")]

    # The next run reads the cached quarters instead of asking for the whole tile again.
    requested.clear()
    assert len(locator.fetch_substation_tile(32, -81)) == 4
    assert requested == []


def test_a_tile_stops_at_the_first_quarter_that_fails(monkeypatch, empty_cache):
    requested = []
    monkeypatch.setattr(locator, "download_substations", lambda south, west, size: requested.append(size))
    assert locator.fetch_substation_tile(32, -81) is None
    assert requested == [1, 0.5, 0.25]
    assert empty_cache == {}

    # The rest of the run doesn't ask for those tiles again.
    assert locator.fetch_substation_tile(32, -81) is None
    assert requested == [1, 0.5, 0.25]


def test_a_failed_tile_fails_the_search(monkeypatch):
    monkeypatch.setattr(locator, "fetch_substation_tile", lambda south, west: None if south == 33 else [])
    assert locator.search_nearby_substations(32.95, -80.05) is None


@pytest.fixture
def no_network(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("an overridden location must not be searched")

    monkeypatch.setattr(locator, "geocode_general_location", fail)
    monkeypatch.setattr(locator, "search_nearby_substations", fail)


def use_overrides(monkeypatch, tmp_path, rows):
    overrides = locator.load_overrides(write_overrides(tmp_path / "overrides.csv", rows))
    monkeypatch.setattr(locator, "OVERRIDES", overrides)


def test_an_override_replaces_the_search(monkeypatch, tmp_path, no_network):
    use_overrides(monkeypatch, tmp_path, [override()])
    row = locator.locate_project_location(project(), "EVANS PRIMARY", 1)
    assert (row["latitude"], row["longitude"]) == ("33.5", "-82.1")
    assert (row["osm_type"], row["osm_id"], row["matched_name"]) == ("way", "123", "Evans Primary Substation")
    assert (row["confidence"], row["source"]) == ("HIGH", "Manual override")
    assert row["reasons"] == "OSM way 123; Nominatim finds Evans County"
    assert row["location_role"] == "location_1"
    assert list(row) == locator.LOCATION_FIELDS


def test_a_project_override_wins_over_a_utility_wide_one(monkeypatch, tmp_path, no_network):
    use_overrides(monkeypatch, tmp_path, [override(), override(project_id="20793", latitude="33.6")])
    assert locator.locate_project_location(project(), "EVANS PRIMARY", 1)["latitude"] == "33.6"
    assert locator.locate_project_location(project(project_id="17993"), "EVANS PRIMARY", 1)["latitude"] == "33.5"


def test_an_override_only_covers_its_own_utility(monkeypatch, tmp_path):
    use_overrides(monkeypatch, tmp_path, [override()])
    searched = []
    monkeypatch.setattr(locator, "geocode_general_location", lambda name, state: searched.append(name) or (None, False))
    row = locator.locate_project_location(project(utility=DESC, project_id="6810 A"), "Evans Primary", 1)
    assert searched == ["Evans"]
    assert row["source"] == "No match"


def test_overridden_points_feed_the_project_center(monkeypatch, tmp_path, no_network):
    use_overrides(monkeypatch, tmp_path, [override(), override(target_location="THURMOND DAM", latitude="33.7", longitude="-82.2")])
    rows = [locator.locate_project_location(project(), name, number) for number, name in enumerate(project()["locations"], start=1)]
    [summary] = locator.build_project_summaries([project()], rows)
    assert summary["overall_confidence"] == "HIGH"
    assert summary["centroid_latitude"] == pytest.approx(33.6)
    assert summary["centroid_longitude"] == pytest.approx(-82.15)


def test_an_override_with_blank_coordinates_removes_a_wrong_point(monkeypatch, tmp_path, no_network):
    blank = override(latitude="", longitude="", matched_name="", osm_type="", osm_id="",
                     source="PDF: about 2.3 miles from Thurmond", note="Nominatim finds Hooks Pond")
    use_overrides(monkeypatch, tmp_path, [blank, override(target_location="THURMOND DAM", latitude="33.7", longitude="-82.2")])
    rows = [locator.locate_project_location(project(), name, number) for number, name in enumerate(project()["locations"], start=1)]
    assert (rows[0]["latitude"], rows[0]["longitude"], rows[0]["confidence"]) == ("", "", "LOW")
    assert rows[0]["reasons"] == "PDF: about 2.3 miles from Thurmond; Nominatim finds Hooks Pond"
    [summary] = locator.build_project_summaries([project()], rows)
    assert (summary["located_locations"], summary["overall_confidence"]) == (1, "LOW")
    assert (summary["centroid_latitude"], summary["centroid_longitude"]) == (33.7, -82.2)


def test_no_overrides_file_means_no_overrides(tmp_path):
    assert locator.load_overrides(tmp_path / "missing.csv") == {}


@pytest.mark.parametrize(
    "rows, fields, message",
    [
        ([override()], locator.OVERRIDE_FIELDS[:-1], "must have the columns"),
        ([override(latitude="north")], locator.OVERRIDE_FIELDS, "must both be numbers"),
        ([override(longitude="")], locator.OVERRIDE_FIELDS, "must both be numbers"),
        ([override(source="")], locator.OVERRIDE_FIELDS, "are required"),
        ([override(), override(target_location="EVANS PRIMARY")], locator.OVERRIDE_FIELDS, "a second override"),
    ],
)
def test_a_malformed_overrides_file_stops_the_run(tmp_path, rows, fields, message):
    rows = [{key: row[key] for key in fields} for row in rows]
    with pytest.raises(SystemExit, match=message):
        locator.load_overrides(write_overrides(tmp_path / "overrides.csv", rows, fields))


def test_the_committed_overrides_file_loads():
    assert locator.load_overrides() == locator.OVERRIDES
