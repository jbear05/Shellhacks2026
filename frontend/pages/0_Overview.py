import streamlit as st
from frontend.project_data import DESC, GEORGIA, ROOT, load_demo_projects
from frontend.ui import render_shell

render_shell("Gridlock")
st.title("Find the opportunity between two plans.")
st.write("Gridlock compares public transmission construction plans to find nearby projects and opportunities to coordinate their build windows.")
a, b, c = st.columns([1.7, 1.1, 1.1])
a.metric("Geographic signal", "25 miles")
b.metric("Compare build windows", "Timing")
c.metric("DESC + Georgia Power", "2 utilities")
st.info("The demo uses the supplied 2024–2028 DESC and 2025 Georgia Power plans. Dates describe those filings, not verified current construction status.")
if st.button("Explore the real-data demo", type="primary"):
    st.session_state.projects = load_demo_projects()
    st.session_state.update(utility_a=DESC, utility_b=GEORGIA, threshold_miles=25.0, include_low=True, ranking_mode="distance_first")
    st.switch_page(str(ROOT / "frontend/pages/4_Overlaps.py"))
if st.button("Upload PDFs or project tables"):
    st.switch_page(str(ROOT / "frontend/pages/1_Project_Setup.py"))
st.subheader("From source to decision")
st.write("Load the two organizer PDFs or saved project tables. Review source fields and endpoint evidence, inspect qualifying pairs on the map, then download ranked results and a snapshot you can reopen.")
st.caption("LOW-confidence matches stay flagged. Map connections join project centers; they are not transmission routes. The demo and PDF imports use saved geocoding and make no AI or geocoding API calls.")
