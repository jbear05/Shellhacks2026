"""The map draws the substations behind each center, with no Streamlit server or network."""
import pytest

pytest.importorskip("pydeck")

from frontend.analysis import calculate_overlaps
from frontend.map_view import make_map
from frontend.project_data import DESC, GEORGIA, load_demo_projects


@pytest.fixture(scope="module")
def demo():
    projects = load_demo_projects()
    return projects, calculate_overlaps(projects, DESC, GEORGIA)


def layer(deck, layer_id):
    return next(item for item in deck.layers if item.id == layer_id).data


def test_a_focused_pair_shows_its_substations_and_the_line_its_center_halves(demo):
    projects, results = demo
    pair = results[(results.project_id_a == "6810 A") & (results.project_id_b == "20793")].iloc[0]
    deck = make_map(projects, results, DESC, GEORGIA, selected=pair)
    names = sorted(ring["label"].split(" substation")[0] for ring in layer(deck, "substations"))
    assert names == ["EVANS PRIMARY", "Hooks", "THURMOND DAM", "Thurmond"]
    lines = layer(deck, "center_lines")
    assert len(lines) == 2
    hooks = next(line for line in lines if "Hooks" in line["label"])
    center = next(p for p in layer(deck, "projects") if p["project_id"] == "6810 A")["position"]
    assert center == pytest.approx([(a + b) / 2 for a, b in zip(hooks["start"], hooks["end"])])


def test_substations_are_hidden_until_asked_for(demo):
    projects, results = demo
    assert layer(make_map(projects, results, DESC, GEORGIA), "substations") == []
    shown = layer(make_map(projects, results, DESC, GEORGIA, show_substations=True), "substations")
    assert len(shown) > 200


def test_center_labels_say_how_the_center_was_made(demo):
    projects, results = demo
    labels = {p["project_id"]: p["label"] for p in layer(make_map(projects, results, DESC, GEORGIA), "projects")}
    assert "Center: midpoint of VCS2 and Ward" in labels["06810 F"]
    assert "Center: VCS1 only; Scout has no coordinates" in labels["6853 B-F"]
    assert "Center: Summerville (the project's one substation)" in labels["05004 P"]
