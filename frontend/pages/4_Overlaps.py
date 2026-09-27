import streamlit as st
import pandas as pd
import pydeck as pdk
from math import radians, sin, cos, sqrt, atan2
from data_loader import ProjectLoadError, load_uploaded_projects
from ranking import rank_overlaps
from ui import render_shell

st.set_page_config(
    page_title="Overlap Results",
    page_icon="🔗",
    layout="wide"
)

render_shell("Overlap Results")

st.title("Overlap Results")

if "projects" not in st.session_state:
    st.warning("Please complete the Project Review page first.")
    st.stop()

projects = st.session_state.projects.copy()

utility_a = st.session_state.get("utility_a", "Utility A")
utility_b = st.session_state.get("utility_b", "Utility B")
threshold = st.session_state.get("threshold_miles", 25.0)

# Recover sessions created before uploaded utility labels were normalized.
utility_values = projects.get("Utility", pd.Series(dtype=str)).fillna("").astype(str).str.strip()
if (
    utility_a not in utility_values.values
    or utility_b not in utility_values.values
) and (
    st.session_state.get("files_a")
    or st.session_state.get("files_b")
):
    try:
        refreshed_projects = load_uploaded_projects(
            st.session_state.get("files_a", []),
            st.session_state.get("files_b", []),
            utility_a,
            utility_b,
        )
    except ProjectLoadError:
        refreshed_projects = pd.DataFrame()

    if not refreshed_projects.empty:
        projects = refreshed_projects
        st.session_state.projects = projects

# Handle older sessions whose fixture labels were saved before setup names
# became authoritative.
utility_values = projects.get("Utility", pd.Series(dtype=str)).fillna("").astype(str).str.strip()
available_utilities = list(utility_values.unique())
if (
    utility_a not in available_utilities
    and utility_b not in available_utilities
    and len(available_utilities) == 2
):
    label_a = next(
        (
            label for label in available_utilities
            if label.casefold().replace("_", " ").endswith("utility a")
        ),
        None,
    )
    label_b = next(
        (
            label for label in available_utilities
            if label.casefold().replace("_", " ").endswith("utility b")
        ),
        None,
    )
    if label_a and label_b:
        projects.loc[projects["Utility"] == label_a, "Utility"] = utility_a
        projects.loc[projects["Utility"] == label_b, "Utility"] = utility_b
        st.session_state.projects = projects

st.write(
    f"Showing project pairs within **{threshold:.1f} miles** of each other."
)


def haversine_miles(lat1, lon1, lat2, lon2):
    earth_radius = 3958.8

    lat1, lon1, lat2, lon2 = map(
        radians,
        [lat1, lon1, lat2, lon2]
    )

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    return 2 * earth_radius * atan2(
        sqrt(a),
        sqrt(1 - a)
    )


def iso_date(value):
    if pd.isna(value):
        return ""
    return pd.Timestamp(value).date().isoformat()


def final_overlap_table(ranked_rows):
    """Return the workbook-style table with descriptive ranking categories."""

    def display_value(value):
        if value is None or pd.isna(value) or str(value).strip() == "":
            return "Unavailable"
        return str(value).strip()

    def timeline_value(row):
        if "build windows overlap" in row["ranking_reason"]:
            return "Yes"
        if "build windows do not overlap" in row["ranking_reason"]:
            return "No"
        return "Unavailable"

    return pd.DataFrame([
        {
            "Rank": row["rank"],
            "Utility A Project": row["project_name_a"],
            "Utility B Project": row["project_name_b"],
            "Distance Miles": row["distance_miles"],
            "Timeline Overlap": timeline_value(row),
            "Utility A Date": row["in_service_date_a"],
            "Utility B Date": row["in_service_date_b"],
            "Date Gap Days": row["days_apart"],
            "Voltage": f"A: {display_value(row['voltage_a'])}; B: {display_value(row['voltage_b'])}",
            "Project Type": f"A: {display_value(row['project_type_a'])}; B: {display_value(row['project_type_b'])}",
        }
        for row in ranked_rows
    ])


# Convert coordinates to numbers
projects["Latitude"] = pd.to_numeric(
    projects["Latitude"],
    errors="coerce"
)

projects["Longitude"] = pd.to_numeric(
    projects["Longitude"],
    errors="coerce"
)

# Convert dates
if "In-Service Date" in projects.columns:
    projects["In-Service Date"] = pd.to_datetime(
        projects["In-Service Date"],
        errors="coerce"
    )

if "Start Date" in projects.columns:
    projects["Start Date"] = pd.to_datetime(
        projects["Start Date"],
        errors="coerce"
    )

utility_a_projects = projects[
    projects["Utility"] == utility_a
]

utility_b_projects = projects[
    projects["Utility"] == utility_b
]

overlaps = []

for _, project_a in utility_a_projects.iterrows():
    for _, project_b in utility_b_projects.iterrows():

        if pd.isna(project_a["Latitude"]) or pd.isna(
            project_a["Longitude"]
        ):
            continue

        if pd.isna(project_b["Latitude"]) or pd.isna(
            project_b["Longitude"]
        ):
            continue

        distance = haversine_miles(
            project_a["Latitude"],
            project_a["Longitude"],
            project_b["Latitude"],
            project_b["Longitude"]
        )

        if distance <= threshold:
            date_gap = None

            if (
                "In-Service Date" in projects.columns
                and pd.notna(project_a["In-Service Date"])
                and pd.notna(project_b["In-Service Date"])
            ):
                date_gap = abs(
                    (
                        project_a["In-Service Date"]
                        - project_b["In-Service Date"]
                    ).days
                )

            overlaps.append({
                "utility_a": utility_a,
                "project_id_a": project_a["Project ID"],
                "project_name_a": project_a["Project Name"],
                "project_type_a": project_a["Project Type"],
                "start_date_a": iso_date(project_a.get("Start Date")),
                "in_service_date_a": iso_date(project_a.get("In-Service Date")),
                "voltage_a": project_a.get("Voltage 1", ""),
                "utility_b": utility_b,
                "project_id_b": project_b["Project ID"],
                "project_name_b": project_b["Project Name"],
                "project_type_b": project_b["Project Type"],
                "start_date_b": iso_date(project_b.get("Start Date")),
                "in_service_date_b": iso_date(project_b.get("In-Service Date")),
                "voltage_b": project_b.get("Voltage 1", ""),
                "distance_miles": round(distance, 2),
                "days_apart": date_gap,
            })

ranked_overlaps = rank_overlaps(overlaps)
overlap_df = final_overlap_table(ranked_overlaps)

st.session_state.overlaps = overlap_df

map_panel = st.container(border=True)
map_panel.subheader("Overlap radius map")
map_panel.caption(
    "Each circle represents the configured overlap radius. Intersecting circles "
    "show where projects from the two utilities are close enough to be compared."
)

map_projects = projects.dropna(subset=["Latitude", "Longitude"]).copy()

if map_projects.empty:
    map_panel.info("No projects with coordinates are available to map.")
else:
    center_latitude = map_projects["Latitude"].mean()
    center_longitude = map_projects["Longitude"].mean()

    map_layers = []
    utility_layer_colors = [
        (utility_a, [35, 126, 255, 70], [35, 126, 255, 255]),
        (utility_b, [255, 140, 50, 70], [255, 140, 50, 255]),
    ]

    for utility_name, radius_color, center_color in utility_layer_colors:
        utility_projects = map_projects[
            map_projects["Utility"] == utility_name
        ]
        if utility_projects.empty:
            continue

        map_layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=utility_projects,
                get_position="[Longitude, Latitude]",
                get_radius=threshold * 1609.344,
                get_fill_color=radius_color,
                get_line_color=radius_color,
                get_line_width=1,
                stroked=True,
                filled=True,
                pickable=True,
            )
        )
        map_layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=utility_projects,
                get_position="[Longitude, Latitude]",
                get_radius=700,
                get_fill_color=center_color,
                get_line_color=[255, 255, 255, 255],
                get_line_width=2,
                stroked=True,
                filled=True,
                pickable=True,
            )
        )

    overlap_deck = pdk.Deck(
        map_style=None,
        initial_view_state=pdk.ViewState(
            latitude=center_latitude,
            longitude=center_longitude,
            zoom=7,
            pitch=0,
        ),
        layers=map_layers,
        tooltip={
            "html": (
                "<b>{Project Name}</b><br/>"
                "{Utility}<br/>"
                "{Project Type}<br/>"
                f"Radius: {threshold:.1f} miles"
            ),
            "style": {"backgroundColor": "#111827", "color": "white"},
        },
    )
    map_panel.pydeck_chart(overlap_deck, use_container_width=True)

summary_panel = st.container(border=True)
col1, col2, col3 = summary_panel.columns(3)

with col1:
    st.metric("Utility A Projects", len(utility_a_projects))

with col2:
    st.metric("Utility B Projects", len(utility_b_projects))

with col3:
    st.metric("Overlapping Pairs", len(overlap_df))

st.divider()

results_panel = st.container(border=True)
if overlap_df.empty:
    results_panel.info("No overlapping project pairs were found.")

    if not utility_a_projects.empty and not utility_b_projects.empty:
        results_panel.caption(
            "Both utilities have project rows with coordinates, but none are "
            f"within {threshold:.1f} miles."
        )
    else:
        available_utilities = sorted(
            projects["Utility"].dropna().astype(str).unique()
        )
        results_panel.warning(
            "The selected utility names do not match the imported project rows. "
            f"Utility A rows: {len(utility_a_projects)}; "
            f"Utility B rows: {len(utility_b_projects)}; "
            f"Imported labels: {available_utilities}"
        )
else:
    results_panel.subheader("Ranked Overlapping Project Pairs")

    results_panel.dataframe(
        overlap_df,
        use_container_width=True,
        hide_index=True
    )

    csv_data = overlap_df.to_csv(index=False)

    results_panel.download_button(
        "Download Ranked Overlap CSV",
        data=csv_data,
        file_name="ranked_overlap_results.csv",
        mime="text/csv"
    )

if st.button("Continue to Export"):
    st.switch_page("pages/5_Export.py")