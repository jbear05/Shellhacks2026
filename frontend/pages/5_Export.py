import streamlit as st
from frontend.data_loader import prepare_projects
from frontend.workspace import analyze_state, export_bundle, settings_from_state
from frontend.ui import render_shell

render_shell("Export Results")
st.title("Export Results")
if "projects" not in st.session_state:
    st.info("Load project data first.")
    st.stop()
try:
    projects = prepare_projects(st.session_state.projects)
    results = analyze_state(st.session_state)
except ValueError as error:
    st.warning(str(error))
    st.stop()
st.write("Results are recalculated from current projects, reviews and settings. The snapshot preserves the inputs and settings so you can reopen the analysis.")
a, b = st.columns(2)
a.metric("Projects", len(projects))
b.metric("Qualifying pairs", len(results))
st.download_button("Download analysis snapshot", export_bundle(projects, results, settings_from_state(st.session_state)), "gridlock_snapshot.zip", "application/zip", type="primary")
a, b = st.columns(2)
a.download_button("Download project table", projects.to_csv(index=False), "project_table.csv", "text/csv")
b.download_button("Download ranked overlap table", results.to_csv(index=False), "ranked_overlap_results.csv", "text/csv")
st.caption("Restore the snapshot on Project Setup. Source evidence and LOW-confidence flags remain in the exports.")
with st.expander("Preview exported pairs"):
    st.dataframe(results, hide_index=True, width="stretch")
