import streamlit as st
import pandas as pd
from math import radians, sin, cos, sqrt, atan2
from data_loader import ProjectLoadError, load_uploaded_projects
from ui import render_shell

st.set_page_config(
    page_title="Overlap Results",
    page_icon="🔗",
    layout="wide"
)

render_shell("Overlap Results")

st.title("🔗 Overlap Results")

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
                "Utility A Project": project_a["Project Name"],
                "Utility B Project": project_b["Project Name"],
                "Distance Miles": round(distance, 2),
                "Utility A Date": project_a["In-Service Date"],
                "Utility B Date": project_b["In-Service Date"],
                "Date Gap Days": date_gap
            })

overlap_df = pd.DataFrame(overlaps)

st.session_state.overlaps = overlap_df

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
    results_panel.subheader("Overlapping Project Pairs")

    results_panel.dataframe(
        overlap_df,
        use_container_width=True,
        hide_index=True
    )

    csv_data = overlap_df.to_csv(index=False)

    results_panel.download_button(
        "Download Overlap CSV",
        data=csv_data,
        file_name="overlap_results.csv",
        mime="text/csv"
    )

if st.button("Continue to Export"):
    st.switch_page("pages/5_Export.py")