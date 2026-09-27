import streamlit as st
import pandas as pd
from ui import render_shell

st.set_page_config(
    page_title="Export Results",
    page_icon="📤",
    layout="wide"
)

render_shell("Export Results")

st.title("Export Results")

projects = st.session_state.get(
    "projects",
    pd.DataFrame()
)

overlaps = st.session_state.get(
    "overlaps",
    pd.DataFrame()
)

if projects.empty:
    st.warning("No project data is available to export.")
    st.stop()

st.write(
    "Download your project data and overlap results."
)

project_export_panel = st.container(border=True)
project_export_panel.subheader("Project Data")

projects_csv = projects.to_csv(index=False)

project_export_panel.download_button(
    label="Download Project Table",
    data=projects_csv,
    file_name="project_table.csv",
    mime="text/csv"
)

overlap_export_panel = st.container(border=True)
overlap_export_panel.subheader("Overlap Data")

if overlaps.empty:
    overlap_export_panel.info("No overlap results are available.")
else:
    overlaps_csv = overlaps.to_csv(index=False)

    overlap_export_panel.download_button(
        label="Download Ranked Overlap Table",
        data=overlaps_csv,
        file_name="ranked_overlap_results.csv",
        mime="text/csv"
    )

summary_panel = st.container(border=True)
summary_panel.subheader("Summary")

col1, col2, col3 = summary_panel.columns(3)

with col1:
    st.metric("Total Projects", len(projects))

with col2:
    confirmed = 0

    if "Match Status" in projects.columns:
        confirmed = (
            projects["Match Status"] == "Confirmed"
        ).sum()

    st.metric("Confirmed Locations", confirmed)

with col3:
    st.metric("Overlap Pairs", len(overlaps))

st.divider()

preview_panel = st.container(border=True)
preview_panel.subheader("Preview")

tab1, tab2 = st.tabs([
    "Project Table",
    "Overlap Table"
])

with tab1:
    preview_panel.dataframe(
        projects,
        use_container_width=True,
        hide_index=True
    )

with tab2:
    if overlaps.empty:
        preview_panel.info("No overlap results available.")
    else:
        preview_panel.dataframe(
            overlaps,
            use_container_width=True,
            hide_index=True
        )