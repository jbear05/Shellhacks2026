"""Entry point supporting both root and frontend launch commands."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st


def main():
    st.set_page_config(page_title="Gridlock", page_icon="⚡", layout="wide")
    for key, value in {"threshold_miles": 25.0, "include_low": True, "ranking_mode": "score"}.items():
        st.session_state.setdefault(key, value)
    # Keep analysis settings when navigating to pages without their widgets.
    for key in ("utility_a", "utility_b", "threshold_miles", "include_low", "ranking_mode"):
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]
    pages = [
        ("0_Overview.py", "Gridlock"),
        ("1_Project_Setup.py", "Project Setup"),
        ("2_Project_Review.py", "Project Review"),
        ("3_Location_Confirm.py", "Location Verification"),
        ("4_Overlaps.py", "Overlap Results"),
        ("5_Export.py", "Export Results"),
    ]
    navigation = st.navigation([
        st.Page(str(ROOT / "frontend" / "pages" / filename), title=title, default=index == 0)
        for index, (filename, title) in enumerate(pages)
    ])
    st.sidebar.caption("Public construction plans · ShellHacks 2026")
    if "projects" in st.session_state:
        st.sidebar.caption(f"{len(st.session_state.projects)} projects loaded")
    navigation.run()


if __name__ == "__main__":
    main()
