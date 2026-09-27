import pytest
import pandas as pd
from unittest.mock import patch

from frontend.data_loader import ProjectLoadError
from frontend.pdf_import import parse_known_pdf
from frontend.project_data import DESC, GEORGIA, ROOT, SOURCE_FILES, load_demo_projects


def test_unknown_pdf_is_rejected_before_any_parser_or_network_call():
    with pytest.raises(ProjectLoadError, match="not one of the two supported"):
        parse_known_pdf(b"%PDF-another-public-plan")


@pytest.mark.slow
@pytest.mark.parametrize("utility", [DESC, GEORGIA])
def test_real_uploaded_pdf_matches_saved_demo(utility):
    with patch("parsers.ai_parser.llm.Model.ask", side_effect=AssertionError("AI called during upload")):
        parsed = parse_known_pdf((ROOT / SOURCE_FILES[utility]).read_bytes())
    demo = load_demo_projects()
    expected = demo[demo.Utility == utility].reset_index(drop=True)
    actual = parsed.drop(columns="Source SHA256").reset_index(drop=True)
    pd.testing.assert_frame_equal(actual, expected[actual.columns], check_dtype=False)
    assert set(parsed.Utility) == {utility}
    assert parsed["Source SHA256"].str.len().eq(64).all()
