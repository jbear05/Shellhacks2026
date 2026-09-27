"""Map project centers as overlap-radius circles (pydeck)."""
from __future__ import annotations

import pandas as pd
import pydeck as pdk

from frontend.analysis import eligible_projects

METERS_PER_MILE = 1609.344


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


def make_map(
    projects,
    results,
    utility_a,
    utility_b,
    include_low=True,
    selected=None,
    threshold_miles=25.0,
):
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
                get_radius=threshold_miles * METERS_PER_MILE,
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
