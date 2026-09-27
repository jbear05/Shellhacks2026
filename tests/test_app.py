"""Exercise the actual Streamlit page flow without network requests."""
import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

from frontend.project_data import ROOT


def click(app, label):
    next(button for button in app.button if button.label == label).click().run()
    assert not app.exception
    # AppTest does not persist a page change triggered by st.switch_page itself.
    destinations = {"Explore the real-data demo": "4_Overlaps.py", "Upload PDFs or project tables": "1_Project_Setup.py",
                    "Continue to Project Review": "2_Project_Review.py", "Continue to Location Verification": "3_Location_Confirm.py",
                    "Continue to Overlap Results": "4_Overlaps.py", "Continue to Export": "5_Export.py"}
    if label in destinations:
        app.switch_page("frontend/pages/" + destinations[label]).run()
        assert not app.exception


def test_demo_filters_reviews_and_exports_share_current_settings():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception
    click(app, "Explore the real-data demo")
    assert len(app.session_state["overlaps"]) == 73
    app.checkbox[0].uncheck().run()
    assert not app.exception
    assert len(app.session_state["overlaps"]) == 53
    app.selectbox[-1].select(0).run()
    assert not app.exception
    assert any("Opportunity #" in value.value for value in app.subheader)
    assert any("Rough impact estimate" in value.value for value in app.markdown)
    pairs = app.session_state["overlaps"]
    unestimated_pair = pairs[pairs.land_saved_value_usd.isna()].index[0]
    app.selectbox[-1].select(unestimated_pair).run()
    assert not app.exception
    assert any("No estimate:" in value.value for value in app.markdown)
    estimated_pair = pairs[(pairs.project_id_a == "6810 A") & (pairs.project_id_b == "20793")].index[0]
    app.selectbox[-1].select(estimated_pair).run()
    assert not app.exception
    assert next(metric.value for metric in app.metric if metric.label == "Land a shared corridor could save") == "27.9 acres"
    assert next(metric.value for metric in app.metric if metric.label == "Land value") == "$137,303"
    assert any("2.3 miles" in value.value for value in app.markdown)
    app.checkbox(key="show_circles").uncheck().run()
    assert not app.exception
    app.checkbox(key="show_substations").check().run()
    assert not app.exception
    app.switch_page("frontend/pages/2_Project_Review.py").run()
    assert not app.exception
    click(app, "Save Project Changes")
    click(app, "Continue to Location Verification")
    click(app, "Save Location Reviews")
    click(app, "Continue to Overlap Results")
    assert app.session_state["include_low"] is False
    assert len(app.session_state["overlaps"]) == 53
    click(app, "Continue to Export")
    assert len(app.get("download_button")) == 3
    assert next(metric.value for metric in app.metric if metric.label == "Qualifying pairs") == "53"


def test_setup_saved_plans_and_same_utility_guard():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    click(app, "Upload PDFs or project tables")
    click(app, "Load public plans")
    click(app, "Continue to Project Review")
    app.switch_page("frontend/pages/4_Overlaps.py").run()
    assert not app.exception
    app.selectbox(key="utility_b").select(app.session_state["utility_a"]).run()
    assert not app.exception
    assert any("distinct" in warning.value for warning in app.warning)


def test_empty_results_export_without_stale_previous_pairs():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    click(app, "Explore the real-data demo")
    app.number_input[0].set_value(1.0).run()
    assert app.session_state["overlaps"].empty
    assert not app.exception
    click(app, "Continue to Export")
    assert next(metric.value for metric in app.metric if metric.label == "Qualifying pairs") == "0"
