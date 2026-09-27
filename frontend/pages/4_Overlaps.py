import streamlit as st
from frontend.analysis import eligible_projects
from frontend.map_view import make_map
from frontend.project_data import ROOT
from frontend.workspace import analyze_state
from frontend.ui import render_shell

render_shell("Overlap Results")
st.title("Coordination opportunities")
if "projects" not in st.session_state:
    st.info("Load the real-data demo or upload project data first.")
    st.stop()
projects = st.session_state.projects
utilities = list(projects.Utility.unique())
a, b, c = st.columns([2, 2, 1])
a.selectbox("Compare utility", utilities, key="utility_a")
b.selectbox("With utility", utilities, key="utility_b")
c.number_input("Within miles", min_value=1.0, max_value=100.0, key="threshold_miles")
st.checkbox("Include LOW-confidence candidates", key="include_low")
st.selectbox("Ranking policy", ["distance_first", "score"], format_func=lambda v: "Distance bands, then timing" if v == "distance_first" else "Equal-weight total score", key="ranking_mode")
st.caption("Default order: ≤5 / ≤15 / ≤25 mile bands, then overlapping build windows, date gap, voltage and type. Unknown timing stays unknown. The 0–15 score is supplementary in distance-first mode.")
try:
    results = analyze_state(st.session_state)
except ValueError as error:
    st.warning(str(error))
    st.stop()
st.session_state.overlaps = results
eligible = eligible_projects(projects, st.session_state.include_low)
selected_utilities = projects[projects.Utility.isin([st.session_state.utility_a, st.session_state.utility_b])]
usable = eligible[eligible.Utility.isin([st.session_state.utility_a, st.session_state.utility_b])]
a, b, c, d = st.columns(4)
a.metric("Source projects", len(selected_utilities))
b.metric("Eligible centers", len(usable))
c.metric("Nearby pairs", len(results))
d.metric("Overlapping build windows", int((results.timeline_overlap == "Yes").sum()))
st.caption("Dates describe the supplied plans, not verified current construction status. LOW locations may be place-name fallbacks; inspect their evidence.")
selected = None
if not results.empty:
    choice = st.selectbox("Focus an opportunity", list(results.index), index=None, placeholder="Show all projects and qualifying pairs", format_func=lambda i: f"#{results.loc[i, 'rank']} · {results.loc[i, 'project_id_a']} ↔ {results.loc[i, 'project_id_b']} · {float(results.loc[i, 'distance_miles']):.2f} mi")
    if choice is not None:
        selected = results.loc[choice]
st.subheader("Project map")
st.checkbox("Show the substations behind every center", key="show_substations", help="A focused pair always shows its substations.")
st.caption(f"Blue: {st.session_state.utility_a}. Orange: {st.session_state.utility_b}. Larger points have qualifying pairs. Rings are substations; a center on the thin line between two rings is their midpoint, and a faint center is the only located one of two substations. All lines are straight, not transmission routes. Click a point or connection for details; pan and zoom to explore.")
event = st.pydeck_chart(make_map(projects, results, st.session_state.utility_a, st.session_state.utility_b, st.session_state.include_low, selected, st.session_state.get("show_substations", False)), height=520, on_select="rerun", selection_mode="single-object", key="opportunity_map")
for obj in event.selection.objects.get("projects", []):
    project = projects[(projects.Utility == obj.get("utility")) & (projects["Project ID"] == obj.get("project_id"))]
    st.subheader("Selected project")
    st.dataframe(project, hide_index=True, width="stretch")
for obj in event.selection.objects.get("opportunities", []):
    matching = results[results.overlap_id == obj.get("overlap_id")]
    if not matching.empty:
        selected = matching.iloc[0]
if results.empty:
    if usable.Utility.nunique() < 2:
        st.info("Both utilities need an eligible center. Review missing coordinates, exclusions and the confidence filter.")
    else:
        st.info("No cross-utility pairs meet the distance threshold with these settings.")
else:
    if selected is not None:
        st.subheader(f"Opportunity #{selected['rank']}")
        a, b = st.columns(2)
        for panel, suffix in ((a, "a"), (b, "b")):
            panel.markdown(f"**{selected[f'utility_{suffix}']} · {selected[f'project_id_{suffix}']}**")
            panel.write(selected[f"project_name_{suffix}"])
            panel.write(f"In service: {selected[f'in_service_date_{suffix}'] or 'Unknown'} · Confidence: {selected[f'confidence_{suffix}']}")
            panel.caption(f"Source: {selected[f'source_file_{suffix}']} · Pages: {selected[f'source_pages_{suffix}'] or 'Find by project ID'}")
            with panel.expander("Location evidence"):
                st.write(selected[f"verification_notes_{suffix}"] or "No supporting location notes supplied.")
        st.write(selected["ranking_reason"])
        if selected["confidence_a"] == "Low" or selected["confidence_b"] == "Low":
            st.warning("This pair includes a LOW-confidence location. Confirm its endpoint evidence before treating it as an opportunity.")
    st.subheader("Ranked pairs")
    columns = ["rank", "project_id_a", "project_name_a", "project_id_b", "project_name_b", "distance_miles", "timeline_overlap", "days_apart", "confidence_a", "confidence_b", "total_score", "ranking_reason"]
    st.dataframe(results[columns], width="stretch", hide_index=True, column_config={"distance_miles": st.column_config.NumberColumn("Distance (mi)", format="%.2f"), "total_score": "Supporting score / 15"})
    st.download_button("Download ranked overlap CSV", results.to_csv(index=False), "ranked_overlap_results.csv", "text/csv")
if st.button("Continue to Export"):
    st.switch_page(str(ROOT / "frontend/pages/5_Export.py"))
