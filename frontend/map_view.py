"""Map only the centers and qualifying connections produced by the analysis."""
from __future__ import annotations

import pandas as pd
import pydeck as pdk

from frontend.analysis import eligible_projects


def make_map(projects, results, utility_a, utility_b, include_low=True, selected=None):
    eligible = eligible_projects(projects, include_low)
    eligible = eligible[eligible.Utility.isin([utility_a, utility_b])]
    matched = {(str(row[f"utility_{s}"]), str(row[f"project_id_{s}"])) for row in results.to_dict("records") for s in ("a", "b")}
    points = []
    for row in eligible.to_dict("records"):
        key = (row["Utility"], row["Project ID"])
        points.append({"position": [float(row["Longitude"]), float(row["Latitude"])],
                       "project_id": key[1], "utility": key[0],
                       "color": [35, 126, 255, 230] if key[0] == utility_a else [245, 140, 45, 230],
                       "radius": 8 if key in matched else 4,
                       "label": f"{row['Project Name']}\n{key[0]} · {key[1]}\nConfidence: {row['Confidence']}\n{'Has coordination candidates' if key in matched else 'No qualifying pair'}"})
    connections = []
    for row in results.to_dict("records"):
        focus = selected is not None and row["overlap_id"] == selected["overlap_id"]
        connections.append({"start": [float(row["longitude_a"]), float(row["latitude_a"])],
                            "end": [float(row["longitude_b"]), float(row["latitude_b"])],
                            "overlap_id": row["overlap_id"], "color": [0, 190, 145, 255] if focus else [75, 120, 120, 95],
                            "width": 5 if focus else 2,
                            "label": f"Rank {row['rank']}: {row['project_id_a']} ↔ {row['project_id_b']}\n{float(row['distance_miles']):.2f} miles · Build windows: {row['timeline_overlap']}\nCenter-to-center connection, not a transmission route"})
    if selected is not None:
        lat = (float(selected["latitude_a"]) + float(selected["latitude_b"])) / 2
        lon = (float(selected["longitude_a"]) + float(selected["longitude_b"])) / 2
        zoom = 9
    else:
        lat = pd.to_numeric(eligible.Latitude).mean() if len(eligible) else 33
        lon = pd.to_numeric(eligible.Longitude).mean() if len(eligible) else -81
        zoom = 6
    return pdk.Deck(
        map_provider="carto", map_style="light",
        initial_view_state=pdk.ViewState(latitude=lat, longitude=lon, zoom=zoom),
        layers=[
            pdk.Layer("LineLayer", connections, id="opportunities", get_source_position="start", get_target_position="end", get_color="color", get_width="width", pickable=True),
            pdk.Layer("ScatterplotLayer", points, id="projects", get_position="position", get_fill_color="color", get_radius="radius", radius_units=pdk.types.String("pixels"), radius_min_pixels=4, radius_max_pixels=8, pickable=True),
        ], tooltip={"text": "{label}"},
    )
