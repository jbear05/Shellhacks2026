from __future__ import annotations

import inspect

import pandas as pd
import pydeck as pdk
import streamlit as st
from frontend.analysis import eligible_projects
from frontend.map_view import make_map
from frontend.land_value_reference import estimate_overlap_impact, land_value_per_acre, utility_state
from frontend.project_data import ROOT
from frontend.workspace import analyze_state
from frontend.ui import render_shell


def _paired_projects(projects, results, utility_a, utility_b, include_low):
    eligible = eligible_projects(projects, include_low)
    eligible = eligible[eligible.Utility.isin([utility_a, utility_b])]
    if results is None or getattr(results, "empty", True):
        return eligible.iloc[0:0].copy()

    required_columns = {
        "utility_a",
        "project_id_a",
        "utility_b",
        "project_id_b",
    }
    if not required_columns.issubset(set(results.columns)):
        return eligible.iloc[0:0].copy()

    paired_keys = set()
    for suffix in ("a", "b"):
        utility_column = f"utility_{suffix}"
        project_id_column = f"project_id_{suffix}"
        paired_keys.update(
            zip(
                results[utility_column].astype(str).str.strip(),
                results[project_id_column].astype(str).str.strip(),
            )
        )

    if not paired_keys:
        return eligible.iloc[0:0].copy()

    keys = list(
        zip(
            eligible["Utility"].astype(str).str.strip(),
            eligible["Project ID"].astype(str).str.strip(),
        )
    )
    return eligible[pd.Series(keys, index=eligible.index).isin(paired_keys)].copy()


def _best_overlap_for_project(results, project):
    if results is None or getattr(results, "empty", True) or project is None or project.empty:
        return None

    row = project.iloc[0]
    matches = results[
        (
            (results["utility_a"] == row["Utility"])
            & (results["project_id_a"] == row["Project ID"])
        )
        | (
            (results["utility_b"] == row["Utility"])
            & (results["project_id_b"] == row["Project ID"])
        )
    ]
    if matches.empty:
        return None
    return matches.sort_values(["rank", "distance_miles"]).iloc[0]


def _render_impact_estimate(pair):
    estimate_panel = st.container(border=True)
    impact = estimate_overlap_impact(pair, pair)
    state_a = impact["utility_state_a"]
    state_b = impact["utility_state_b"]
    value_a = impact["land_value_per_acre_a"]
    value_b = impact["land_value_per_acre_b"]
    estimate_panel.markdown("**Rough impact estimate**")
    estimate_panel.write(
        f"Using the USDA 2026 average farm real-estate value per acre (${value_a:,.0f} in {state_a} and ${value_b:,.0f} in {state_b}) and a simple footprint rule ({impact['estimated_acres_a']:.1f} acres for {pair.get('project_type_a', 'Unknown')} vs. {impact['estimated_acres_b']:.1f} acres for {pair.get('project_type_b', 'Unknown')}), "
        f"this pair could potentially share about {impact['estimated_shared_acres']:.1f} acres and avoid roughly ${impact['estimated_land_savings_usd']:,.0f} in land value."
    )
    estimate_panel.caption(
        "This is a rough planning estimate, not an appraisal. It uses the smaller project footprint as the shareable land proxy and USDA 2026 state averages as the land-value reference."
    )


def build_overlap_map(
    projects,
    results,
    utility_a,
    utility_b,
    include_low,
    selected,
    threshold_miles,
):
    if "display_mode" in inspect.signature(make_map).parameters:
        return make_map(
            projects,
            results,
            utility_a,
            utility_b,
            include_low,
            selected,
            threshold_miles,
        )

    map_projects = _paired_projects(projects, results, utility_a, utility_b, include_low)
    map_projects = map_projects.dropna(subset=["Latitude", "Longitude"]).copy()
    if map_projects.empty:
        lat, lon, zoom = 33.0, -81.0, 6
    elif selected is not None:
        lat = (float(selected["latitude_a"]) + float(selected["latitude_b"])) / 2
        lon = (float(selected["longitude_a"]) + float(selected["longitude_b"])) / 2
        zoom = 9
    else:
        lat = float(pd.to_numeric(map_projects["Latitude"]).mean())
        lon = float(pd.to_numeric(map_projects["Longitude"]).mean())
        zoom = 7

    layers: list[pdk.Layer] = []
    utility_layer_colors = [
        (utility_a, [35, 126, 255, 55], [18, 74, 168, 255], [35, 126, 255, 120]),
        (utility_b, [255, 140, 50, 55], [173, 93, 24, 255], [255, 140, 50, 120]),
    ]

    for utility_name, radius_color, center_color, hover_line_color in utility_layer_colors:
        utility_projects = map_projects[map_projects["Utility"] == utility_name]
        if utility_projects.empty:
            continue

        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=utility_projects,
                id=f"radius_{utility_name}",
                get_position="[Longitude, Latitude]",
                get_radius=threshold_miles * 1609.344,
                get_fill_color=[*radius_color[:3], 0],
                get_line_color=[*radius_color[:3], 160],
                get_line_width=2,
                stroked=True,
                filled=True,
                pickable=True,
                auto_highlight=True,
                highlight_color=[*hover_line_color[:3], 120],
            )
        )

    if not map_projects.empty:
        centers = map_projects.copy()
        centers["_center_color"] = centers["Utility"].map(
            {utility_a: [18, 74, 168, 255], utility_b: [173, 93, 24, 255]}
        )
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=centers,
                id="projects",
                get_position="[Longitude, Latitude]",
                get_radius=650,
                get_fill_color="_center_color",
                get_line_color="_center_color",
                get_line_width=0,
                stroked=True,
                filled=True,
                pickable=True,
            )
        )

    threshold_label = f"{float(threshold_miles):.1f}"
    return pdk.Deck(
        map_style=None,
        initial_view_state=pdk.ViewState(
            latitude=lat,
            longitude=lon,
            zoom=zoom,
            pitch=0,
        ),
        layers=layers,
        tooltip={
            "html": (
                "<b>{Project Name}</b><br/>"
                "{Utility}<br/>"
                "{Project Type}<br/>"
                f"Radius: {threshold_label} miles"
            ),
            "style": {"backgroundColor": "#111827", "color": "white"},
        },
    )


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
st.subheader("Overlap radius map")
st.caption(
    f"Blue: {st.session_state.utility_a}. Orange: {st.session_state.utility_b}. "
    "Each circle is the configured distance threshold. Switch the map style between "
    "filled radius and outline line. Hover a circle for a faint outline; click a center "
    "point for project details."
)
event = st.pydeck_chart(
    build_overlap_map(
        projects,
        results,
        st.session_state.utility_a,
        st.session_state.utility_b,
        st.session_state.include_low,
        selected,
        st.session_state.threshold_miles,
    ),
    height=520,
    on_select="rerun",
    selection_mode="single-object",
    key="opportunity_map",
)
selected_project = None
for layer_id in ("projects", f"radius_{st.session_state.utility_a}", f"radius_{st.session_state.utility_b}"):
    for obj in event.selection.objects.get(layer_id, []):
        project = projects[
            (projects.Utility == obj.get("Utility"))
            & (projects["Project ID"] == obj.get("Project ID"))
        ]
        if not project.empty:
            selected_project = project
            st.subheader("Selected project")
            st.dataframe(project, hide_index=True, width="stretch")
            break
    else:
        continue
    break
if results.empty:
    if usable.Utility.nunique() < 2:
        st.info("Both utilities need an eligible center. Review missing coordinates, exclusions and the confidence filter.")
    else:
        st.info("No cross-utility pairs meet the distance threshold with these settings.")
else:
    active_pair = selected or _best_overlap_for_project(results, selected_project)
    if active_pair is not None:
        st.subheader(f"Opportunity #{active_pair['rank']}")
        _render_impact_estimate(active_pair)
        a, b = st.columns(2)
        for panel, suffix in ((a, "a"), (b, "b")):
            panel.markdown(f"**{active_pair[f'utility_{suffix}']} · {active_pair[f'project_id_{suffix}']}**")
            panel.write(active_pair[f"project_name_{suffix}"])
            panel.write(f"In service: {active_pair[f'in_service_date_{suffix}'] or 'Unknown'} · Confidence: {active_pair[f'confidence_{suffix}']}")
            panel.caption(f"Source: {active_pair[f'source_file_{suffix}']} · Pages: {active_pair[f'source_pages_{suffix}'] or 'Find by project ID'}")
            with panel.expander("Location evidence"):
                st.write(active_pair[f"verification_notes_{suffix}"] or "No supporting location notes supplied.")
        st.write(active_pair["ranking_reason"])
        if active_pair["confidence_a"] == "Low" or active_pair["confidence_b"] == "Low":
            st.warning("This pair includes a LOW-confidence location. Confirm its endpoint evidence before treating it as an opportunity.")
    st.subheader("Ranked pairs")
    columns = ["rank", "project_id_a", "project_name_a", "project_id_b", "project_name_b", "distance_miles", "timeline_overlap", "days_apart", "confidence_a", "confidence_b", "total_score", "ranking_reason"]
    st.dataframe(results[columns], width="stretch", hide_index=True, column_config={"distance_miles": st.column_config.NumberColumn("Distance (mi)", format="%.2f"), "total_score": "Supporting score / 15"})
    st.download_button("Download ranked overlap CSV", results.to_csv(index=False), "ranked_overlap_results.csv", "text/csv")
if st.button("Continue to Export"):
    st.switch_page(str(ROOT / "frontend/pages/5_Export.py"))
