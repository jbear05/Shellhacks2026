import streamlit as st
import pandas as pd
from ui import render_shell

st.set_page_config(
    page_title="Project Review",
    page_icon="📋",
    layout="wide"
)

render_shell("Project Review")

st.title("Project Review")

st.write(
    "Review and edit the project information extracted from your uploaded files."
)

# Check whether setup data exists
if "utility_a" not in st.session_state or "utility_b" not in st.session_state:
    st.warning("Please complete Project Setup first.")
    st.stop()

st.write(
    f"Comparing **{st.session_state.utility_a}** "
    f"and **{st.session_state.utility_b}**"
)

if "projects" not in st.session_state or st.session_state.projects.empty:
    st.warning(
        "No project rows were imported. Return to Project Setup and upload a "
        "CSV or XLSX project file."
    )
    st.stop()

project_panel = st.container(border=True)
project_panel.subheader("Project List")

edited_projects = project_panel.data_editor(
    st.session_state.projects,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "Match Status": st.column_config.SelectboxColumn(
            options=[
                "Unmatched",
                "Candidate",
                "Confirmed",
                "Low confidence",
                "Excluded"
            ]
        ),
        "Confidence": st.column_config.SelectboxColumn(
            options=[
                "Low",
                "Medium",
                "High"
            ]
        ),
        "Latitude": st.column_config.NumberColumn(
            format="%.6f"
        ),
        "Longitude": st.column_config.NumberColumn(
            format="%.6f"
        )
    }
)

st.session_state.projects = edited_projects

if st.button("Save Project Changes", type="primary"):
    st.success("Project changes saved.")

st.divider()

col1, col2 = st.columns(2)

with col1:
    confirmed_count = (
        edited_projects["Match Status"] == "Confirmed"
    ).sum()

    st.metric(
        "Confirmed Locations",
        confirmed_count
    )

with col2:
    unmatched_count = (
        edited_projects["Match Status"] == "Unmatched"
    ).sum()

    st.metric(
        "Unmatched Projects",
        unmatched_count
    )

# Download current project data
csv_data = edited_projects.to_csv(index=False)

st.download_button(
    label="Download Project CSV",
    data=csv_data,
    file_name="projects.csv",
    mime="text/csv"
)

if st.button("Continue to Location Verification"):
    st.switch_page("pages/3_Location_Confirm.py")