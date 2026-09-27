"""Map the centers and qualifying connections produced by the analysis, the substations behind each center, and distance circles."""
from __future__ import annotations

import math

import pandas as pd
import pydeck as pdk

from frontend.analysis import eligible_projects
from frontend.data_loader import valid_point

METERS_PER_MILE = 1609.344


def located_endpoints(row):
    """The project's named endpoints that have usable coordinates, as (name, lat, lon, confidence)."""
    points = []
    for number in (1, 2):
        lat, lon = row.get(f"Point {number} Latitude"), row.get(f"Point {number} Longitude")
        if valid_point(lat, lon):
            points.append((str(row.get(f"Point {number} Name") or f"Point {number}"), float(lat), float(lon), row.get(f"Point {number} Confidence") or "Unknown"))
    return points


def center_note(row, points):
    """Say how the center was made, matching prepare_projects' Center Method."""
    named = [str(row.get(f"Point {n} Name")).strip() for n in (1, 2) if str(row.get(f"Point {n} Name") or "").strip()]
    method = row.get("Center Method")
    if method == "endpoint_midpoint" and len(points) == 2:
        return f"Center: midpoint of {points[0][0]} and {points[1][0]}"
    if method == "one_of_two_endpoints" and points:
        missing = [name for name in named if name != points[0][0]]
        return f"Center: {points[0][0]} only; {missing[0] if missing else 'the other substation'} has no coordinates"
    if method == "single_location" and points:
        return f"Center: {points[0][0]} (the project's one substation)"
    return "Center: supplied coordinates"


def fit_view(positions):
    """Center on the positions' bounding box and zoom so it fills most of the map."""
    lons, lats = [p[0] for p in positions], [p[1] for p in positions]
    lon, lat = (min(lons) + max(lons)) / 2, (min(lats) + max(lats)) / 2
    spread = max(max(lons) - min(lons), (max(lats) - min(lats)) * 1.25, 0.01)
    return lat, lon, min(max(math.log2(360 / spread) + 0.8, 6), 12)


def make_map(projects, results, utility_a, utility_b, include_low=True, selected=None, show_substations=False, threshold_miles=None):
    eligible = eligible_projects(projects, include_low)
    eligible = eligible[eligible.Utility.isin([utility_a, utility_b])]
    matched = {(str(row[f"utility_{s}"]), str(row[f"project_id_{s}"])) for row in results.to_dict("records") for s in ("a", "b")}
    focus = set() if selected is None else {(str(selected[f"utility_{s}"]), str(selected[f"project_id_{s}"])) for s in ("a", "b")}
    points, substations, center_lines, circles = [], [], [], []
    for row in eligible.to_dict("records"):
        key = (row["Utility"], row["Project ID"])
        color = [35, 126, 255] if key[0] == utility_a else [245, 140, 45]
        ends = located_endpoints(row)
        fallback = row.get("Center Method") == "one_of_two_endpoints"
        points.append({"position": [float(row["Longitude"]), float(row["Latitude"])],
                       "project_id": key[1], "utility": key[0],
                       # A center that is only one of two substations is drawn faint, with a solid rim.
                       "color": color + [70 if fallback else 230], "line_color": color + [255] if fallback else [255, 255, 255, 230],
                       "radius": 8 if key in matched else 4,
                       "label": f"{row['Project Name']}\n{key[0]} · {key[1]}\nConfidence: {row['Confidence']}\n{center_note(row, ends)}\n{'Has coordination candidates' if key in matched else 'No qualifying pair'}"})
        # Half the threshold, so two centers' circles overlap exactly when the centers are within it.
        if threshold_miles and key in (focus or matched):
            circles.append({"position": points[-1]["position"], "fill_color": color + [30], "line_color": color + [170],
                            "radius": threshold_miles / 2 * METERS_PER_MILE})
        if not (show_substations or key in focus):
            continue
        for name, lat, lon, confidence in ends:
            substations.append({"position": [lon, lat], "color": color + [255], "utility": key[0], "project_id": key[1],
                                "label": f"{name} substation ({confidence})\n{key[0]} · {key[1]}\nAn endpoint of the project, not its center"})
        if len(ends) == 2:
            center_lines.append({"start": [ends[0][2], ends[0][1]], "end": [ends[1][2], ends[1][1]], "color": color + [150],
                                 "label": f"{ends[0][0]} – {ends[1][0]} ({key[1]})\nThe project's center is the middle of this line\nStraight line, not the transmission route"})
    connections = []
    for row in results.to_dict("records"):
        focused = selected is not None and row["overlap_id"] == selected["overlap_id"]
        connections.append({"start": [float(row["longitude_a"]), float(row["latitude_a"])],
                            "end": [float(row["longitude_b"]), float(row["latitude_b"])],
                            "overlap_id": row["overlap_id"], "color": [0, 190, 145, 255] if focused else [75, 120, 120, 95],
                            "width": 5 if focused else 2,
                            "label": f"Rank {row['rank']}: {row['project_id_a']} ↔ {row['project_id_b']}\n{float(row['distance_miles']):.2f} miles · Build windows: {row['timeline_overlap']}\nCenter-to-center connection, not a transmission route"})
    if selected is not None:
        centers = [[float(selected[f"longitude_{s}"]), float(selected[f"latitude_{s}"])] for s in ("a", "b")]
        lat, lon, zoom = fit_view(centers + [s["position"] for s in substations if (s["utility"], s["project_id"]) in focus])
    else:
        lat = pd.to_numeric(eligible.Latitude).mean() if len(eligible) else 33
        lon = pd.to_numeric(eligible.Longitude).mean() if len(eligible) else -81
        zoom = 6
    return pdk.Deck(
        map_provider="carto", map_style="light",
        initial_view_state=pdk.ViewState(latitude=lat, longitude=lon, zoom=zoom),
        layers=[
            pdk.Layer("ScatterplotLayer", circles, id="distance_circles", get_position="position", get_radius="radius", get_fill_color="fill_color", get_line_color="line_color", stroked=True, line_width_min_pixels=1),
            pdk.Layer("LineLayer", center_lines, id="center_lines", get_source_position="start", get_target_position="end", get_color="color", get_width=2, pickable=True),
            pdk.Layer("LineLayer", connections, id="opportunities", get_source_position="start", get_target_position="end", get_color="color", get_width="width", pickable=True),
            pdk.Layer("ScatterplotLayer", substations, id="substations", get_position="position", get_line_color="color", filled=False, stroked=True, get_radius=6, radius_units=pdk.types.String("pixels"), line_width_units=pdk.types.String("pixels"), get_line_width=2, pickable=True),
            pdk.Layer("ScatterplotLayer", points, id="projects", get_position="position", get_fill_color="color", get_line_color="line_color", stroked=True, line_width_units=pdk.types.String("pixels"), get_line_width=1.5, get_radius="radius", radius_units=pdk.types.String("pixels"), radius_min_pixels=4, radius_max_pixels=8, pickable=True),
        ], tooltip={"text": "{label}"},
    )
