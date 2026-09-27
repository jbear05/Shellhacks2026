import streamlit as st
from frontend.data_loader import ProjectLoadError, prepare_projects
from frontend.project_data import ROOT
from frontend.ui import render_shell

render_shell("Project Review")
st.title("Project Review")
if "projects" not in st.session_state:
    st.info("Load project data on Project Setup first.")
    st.stop()
projects = st.session_state.projects.copy()
st.write("Review dates and project attributes. IDs and source evidence are retained. Changes take effect when saved.")
editable = {"Project Name", "Project Type", "Start Date", "In-Service Date", "Voltage 1", "Voltage 2", "Match Status"}
with st.form("project_review"):
    edited = st.data_editor(projects, hide_index=True, width="stretch", disabled=[c for c in projects if c not in editable],
        column_order=["Utility", "Project ID", "Project Name", "Project Type", "Start Date", "In-Service Date", "Voltage 1", "Voltage 2", "Match Status", "Data Warnings", "Source File", "Source Pages"],
        column_config={"Match Status": st.column_config.SelectboxColumn(options=["Unmatched", "Candidate", "Confirmed", "Low confidence", "Excluded"])})
    if st.form_submit_button("Save Project Changes", type="primary"):
        try:
            st.session_state.projects = prepare_projects(edited)
            st.success("Project changes saved. Results will be recalculated.")
        except ProjectLoadError as error:
            st.error(str(error))
warnings = st.session_state.projects[st.session_state.projects["Data Warnings"] != ""]
if len(warnings):
    st.warning(f"{len(warnings)} projects have data or location warnings.")
    with st.expander("Show warnings"):
        st.dataframe(warnings[["Utility", "Project ID", "Data Warnings"]], hide_index=True)
if st.button("Continue to Location Verification"):
    st.switch_page(str(ROOT / "frontend/pages/3_Location_Confirm.py"))
