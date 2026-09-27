import pandas as pd
import streamlit as st
from frontend.project_data import ROOT
from frontend.workspace import apply_location_review
from frontend.ui import render_shell

render_shell("Location Verification")
st.title("Location Verification")
if "projects" not in st.session_state:
    st.info("Load project data on Project Setup first.")
    st.stop()
projects = st.session_state.projects.copy()
st.write("Review endpoints against their evidence. Two usable endpoints give a midpoint; one gives a single-location center. Excluded projects are omitted from analysis.")
a, b, c = st.columns(3)
a.metric("Projects", len(projects))
mapped = projects[["Latitude", "Longitude"]].apply(pd.to_numeric, errors="coerce").notna().all(axis=1)
b.metric("With centers", int(mapped.sum()))
c.metric("Low confidence", int((projects.Confidence == "Low").sum()))
editable = {"Point 1 Latitude", "Point 1 Longitude", "Point 2 Latitude", "Point 2 Longitude", "Latitude", "Longitude", "Location Status", "Confidence", "Verification Notes"}
with st.form("location_review"):
    edited = st.data_editor(projects, width="stretch", hide_index=True, disabled=[c for c in projects if c not in editable],
        column_order=["Utility", "Project ID", "Project Name", "Point 1 Name", "Point 1 Latitude", "Point 1 Longitude", "Point 2 Name", "Point 2 Latitude", "Point 2 Longitude", "Latitude", "Longitude", "Center Method", "Confidence", "Location Status", "Location Source", "Verification Notes"],
        column_config={"Location Status": st.column_config.SelectboxColumn(options=["Missing", "Candidate", "Confirmed", "Excluded"]), "Confidence": st.column_config.SelectboxColumn(options=["Low", "Medium", "High"]), **{c: st.column_config.NumberColumn(format="%.6f") for c in editable if "Latitude" in c or "Longitude" in c}})
    st.caption("Edit endpoints for endpoint-based projects; their center is recalculated. Direct center edits apply to center-only imports. Coordinate changes reset confidence to Low and status to Candidate; confirm them after reviewing evidence.")
    if st.form_submit_button("Save Location Reviews", type="primary"):
        st.session_state.projects, ignored = apply_location_review(projects, edited)
        st.success("Location reviews saved. Centers and results will be recalculated.")
        if ignored:
            st.warning(f"Center edits not applied to {', '.join(ignored)}: their centers come from their endpoints, so edit Point 1 or Point 2 instead.")
with st.expander("Inspect all source evidence"):
    st.dataframe(st.session_state.projects, width="stretch", hide_index=True)
if st.button("Continue to Overlap Results"):
    st.switch_page(str(ROOT / "frontend/pages/4_Overlaps.py"))
