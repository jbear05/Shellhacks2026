import streamlit as st
import pandas as pd
from ui import render_shell

st.set_page_config(
    page_title="Location Verification",
    page_icon="🗺️",
    layout="wide"
)

render_shell("Location Verification")

st.title("🗺️ Location Verification")

if "projects" not in st.session_state:
    st.warning("Please complete the Project Review page first.")
    st.stop()

projects = st.session_state.projects.copy()

# These fields will later be populated by the Overpass matching workflow.
location_defaults = {
    "Location Status": "Missing",
    "Location Source": "",
    "Verification Notes": "",
}

for column, default in location_defaults.items():
    if column not in projects.columns:
        projects[column] = default

if "Confidence" not in projects.columns:
    projects["Confidence"] = "Low"

st.write(
    "Review project locations, prepare Overpass searches, and confirm matches "
    "before calculating overlaps."
)

status_panel = st.container(border=True)
status_panel.subheader("Location status")

col1, col2, col3 = status_panel.columns(3)

with col1:
    st.metric("Projects", len(projects))

with col2:
    mapped_count = projects[["Latitude", "Longitude"]].apply(
        pd.to_numeric,
        errors="coerce"
    ).notna().all(axis=1).sum()
    st.metric("With coordinates", mapped_count)

with col3:
    confirmed_count = (
        projects["Location Status"] == "Confirmed"
    ).sum()
    st.metric("Confirmed locations", confirmed_count)

map_panel = st.container(border=True)
map_panel.subheader("Project map")

map_data = projects.copy()
map_data["Latitude"] = pd.to_numeric(
    map_data["Latitude"],
    errors="coerce"
)
map_data["Longitude"] = pd.to_numeric(
    map_data["Longitude"],
    errors="coerce"
)
map_data = map_data.dropna(subset=["Latitude", "Longitude"])

if map_data.empty:
    map_panel.info(
        "No project coordinates are available yet. Overpass search results "
        "will appear here after a candidate location is selected."
    )
else:
    map_panel.map(
        map_data[["Latitude", "Longitude"]],
        latitude="Latitude",
        longitude="Longitude",
        size=80,
        height=420,
    )

overpass_panel = st.container(border=True)
overpass_panel.subheader("Overpass search")
overpass_panel.caption(
    "This is the setup surface for the Overpass API integration. Search execution "
    "will be added after the map review workflow is connected."
)

col1, col2 = overpass_panel.columns(2)

with col1:
    operator_name = st.text_input(
        "Operator name",
        value=st.session_state.get("utility_a", ""),
        placeholder="Example: Georgia Power"
    )

with col2:
    feature_type = st.selectbox(
        "Infrastructure type",
        options=["substation", "line", "plant"],
        format_func=lambda value: value.title()
    )

col1, col2 = overpass_panel.columns(2)

with col1:
    south_lat = st.number_input("South latitude", value=30.0, format="%.4f")
    west_lon = st.number_input("West longitude", value=-86.0, format="%.4f")

with col2:
    north_lat = st.number_input("North latitude", value=36.0, format="%.4f")
    east_lon = st.number_input("East longitude", value=-78.0, format="%.4f")

if st.button("Prepare Overpass Query"):
    query = f'''[out:json][timeout:25];

(
  nwr["power"="{feature_type}"]["operator"~"{operator_name}",i]
    ({south_lat},{west_lon},{north_lat},{east_lon});
);

out body;
>;
out skel qt;'''
    st.session_state.overpass_query = query
    st.code(query, language="text")
    st.info("Query prepared. API execution and candidate matching are next.")

review_panel = st.container(border=True)
review_panel.subheader("Location review table")

edited_projects = review_panel.data_editor(
    projects,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Latitude": st.column_config.NumberColumn(format="%.6f"),
        "Longitude": st.column_config.NumberColumn(format="%.6f"),
        "Location Status": st.column_config.SelectboxColumn(
            options=["Missing", "Candidate", "Confirmed", "Excluded"]
        ),
        "Confidence": st.column_config.SelectboxColumn(
            options=["Low", "Medium", "High"]
        ),
    },
)

st.session_state.projects = edited_projects

if st.button("Save Location Reviews", type="primary"):
    st.session_state.projects = edited_projects
    st.success("Location review changes saved.")

st.divider()

if st.button("Continue to Overlap Results"):
    st.switch_page("pages/4_Overlaps.py")