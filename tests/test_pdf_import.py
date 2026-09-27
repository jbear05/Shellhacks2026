import pytest

from frontend.data_loader import ProjectLoadError
from frontend.pdf_import import parse_known_pdf
from frontend.project_data import DESC, GEORGIA, ROOT, SOURCE_FILES, load_demo_projects


def test_unknown_pdf_is_rejected_before_any_parser_or_network_call():
    with pytest.raises(ProjectLoadError, match="not one of the two supported"):
        parse_known_pdf(b"%PDF-another-public-plan")


@pytest.mark.slow
@pytest.mark.parametrize("utility", [DESC, GEORGIA])
def test_real_uploaded_pdf_matches_saved_demo(utility):
    parsed = parse_known_pdf((ROOT / SOURCE_FILES[utility]).read_bytes())
    demo = load_demo_projects()
    expected = demo[demo.Utility == utility].set_index("Project ID")
    parsed = parsed.set_index("Project ID")
    assert set(parsed.index) == set(expected.index)
    for field in ("In-Service Date", "Start Date", "Latitude", "Longitude", "Center Method"):
        assert parsed[field].fillna("").to_dict() == expected[field].fillna("").to_dict()
    assert parsed["Source SHA256"].str.len().eq(64).all()
