import argparse
import csv
import json
import math
import os
import re
import time
from urllib.parse import urlencode

import requests

# ==========================================================
# GRIDLOCK - PROJECT LOCATOR
# ==========================================================
# Loops through the 44 DESC projects below, or the projects in a
# parser CSV (--projects-csv), finds general locations with
# Nominatim, searches nearby OSM substations with Overpass,
# scores matches, and saves CSV outputs.
#
#   python gridlock_desc_locator.py
#   python gridlock_desc_locator.py --projects-csv data/processed/georgia_power_projects.csv --output-prefix georgia_power
# ==========================================================

# Utility and state of the built-in DESC list; CSV rows carry their own.
UTILITY = "Dominion Energy South Carolina"
STATE = "South Carolina"
COUNTRY = "USA"
SEARCH_RADIUS_METERS = 25000
NOMINATIM_DELAY_SECONDS = 1.1
OVERPASS_DELAY_SECONDS = 0.5
USER_AGENT = "GridLock-Hackathon/1.0 (student research project)"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

CACHE_FILE = "gridlock_geocode_cache.json"

# Set this to 3 while testing. Leave None to run all projects.
PROJECT_LIMIT = None

OPERATOR_ALIASES = [
    "dominion",
    "dominion energy",
    "dominion energy south carolina",
    "desc",
    "sce&g",
    "south carolina electric & gas",
]

# Project location names below come from the supplied DESC planning PDF.
# Multi-site/line projects intentionally keep multiple named places rather
# than inventing one fake project coordinate.
PROJECTS = [
    {"number": 1, "project_id": "6807 B", "project_name": "Queensboro - Ft Johnson 115 kV & Queensboro-Bayfront 115kV (Queensboro-James Island Sect)", "project_type": "MULTI_LINE", "voltages": ["115000"], "locations": ["Queensboro", "Ft Johnson", "Bayfront", "James Island"]},
    {"number": 2, "project_id": "0167C-D", "project_name": "Union Pier 115-13.8 kV Sub: Tap", "project_type": "SUBSTATION", "voltages": ["115000", "13800"], "locations": ["Union Pier"]},
    {"number": 3, "project_id": "0139 M,N", "project_name": "Okatie 230-115kV Substation, Jasper - Yemassee 230kV #1 Fold-in", "project_type": "BOTH", "voltages": ["230000", "115000"], "locations": ["Okatie", "Jasper", "Yemassee"]},
    {"number": 4, "project_id": "6341 A-F", "project_name": "Cainhoy - Hamlin 115kV: Rebuild Line and Cainhoy - Hamlin 115 kV #2: Construct New 115 kV Line", "project_type": "LINE", "voltages": ["115000"], "locations": ["Cainhoy", "Hamlin"]},
    {"number": 5, "project_id": "6808 J", "project_name": "Eastover - Square D 115kV: Rebuild", "project_type": "LINE", "voltages": ["115000"], "locations": ["Eastover", "Square D"]},
    {"number": 6, "project_id": "6808 K", "project_name": "Burton-St Helena 115kV: Rebuild Burton-Frogmore Transmission Section", "project_type": "LINE", "voltages": ["115000"], "locations": ["Burton", "Frogmore"]},
    {"number": 7, "project_id": "6808 L", "project_name": "Burton-St Helena 115kV: Frogmore Distribution - St Helena", "project_type": "LINE", "voltages": ["115000"], "locations": ["Frogmore", "St Helena"]},
    {"number": 8, "project_id": "6808 N,O", "project_name": "VCS1-Denny Terrace 230kV & VCS1-Pineland 230kV: Rebuild Single Circuit Sections", "project_type": "MULTI_LINE", "voltages": ["230000"], "locations": ["VCS1", "Denny Terrace", "Pineland"]},
    {"number": 9, "project_id": "6808 R", "project_name": "Wateree-Killian 230kV: Rebuild", "project_type": "LINE", "voltages": ["230000"], "locations": ["Wateree", "Killian"]},
    {"number": 10, "project_id": "6808 S", "project_name": "Okatie-Bluffton 115kV: Rebuild", "project_type": "LINE", "voltages": ["115000"], "locations": ["Okatie", "Bluffton"]},
    {"number": 11, "project_id": "6808 U", "project_name": "Hopkins-CIP 230kV: Rebuild", "project_type": "LINE", "voltages": ["230000"], "locations": ["Hopkins", "CIP"]},
    {"number": 12, "project_id": "6808 V", "project_name": "Faber Place-Bayfront 115kV: Rebuild North Bridge Terrace to Bayfront Section", "project_type": "MULTI_LINE", "voltages": ["115000"], "locations": ["Faber Place", "North Bridge Terrace", "Bayfront"]},
    {"number": 13, "project_id": "6808 W", "project_name": "Square D - Hopkins 115kV: Rebuild", "project_type": "LINE", "voltages": ["115000"], "locations": ["Square D", "Hopkins"]},
    {"number": 14, "project_id": "6809 E", "project_name": "Stevens Creek - Hooks 115kV/LR Plumb Branch 46kV Rebuilds", "project_type": "MULTI_LINE", "voltages": ["115000", "46000"], "locations": ["Stevens Creek", "Hooks", "Plumb Branch"]},
    {"number": 15, "project_id": "6809 G", "project_name": "Stevens Creek - Hooks 115kV/LR Plumb Branch 46kV", "project_type": "MULTI_LINE", "voltages": ["115000", "46000"], "locations": ["Stevens Creek", "Hooks", "Plumb Branch"]},
    {"number": 16, "project_id": "6805 G", "project_name": "Edenwood Sub: #1 & #2 230-115kV Autobanks, Replace with 336MVA", "project_type": "SUBSTATION", "voltages": ["230000", "115000"], "locations": ["Edenwood"]},
    {"number": 17, "project_id": "1060A, I, L", "project_name": "Williams St Sub: Replace Sw House & Relays, AM Williams Sub: Replace Sw House, and McMeekin Sub: Add Sw House", "project_type": "MULTI_SITE", "voltages": [], "locations": ["Williams Street", "AM Williams", "McMeekin"]},
    {"number": 18, "project_id": "06005 B", "project_name": "Harleyville 115KV Transmission Tap - Construct (1.4 miles)", "project_type": "LINE", "voltages": ["115000"], "locations": ["Blue Circle", "Harleyville"]},
    {"number": 19, "project_id": "05004 P", "project_name": "Summerville: Replace and Spare 230-115kV 336MVA Auto Bank", "project_type": "SUBSTATION", "voltages": ["230000", "115000"], "locations": ["Summerville"]},
    {"number": 20, "project_id": "06076A", "project_name": "Canadys-Ritter 115KV-Rebld SPDC 230/115KV 1272 (Approx 18 Miles)", "project_type": "LINE", "voltages": ["230000", "115000"], "locations": ["Canadys", "Ritter"]},
    {"number": 21, "project_id": "6359", "project_name": "Yemassee-Ritter 230kV #1 & #2: Construct SPDC with B-1272", "project_type": "LINE", "voltages": ["230000", "115000"], "locations": ["Yemassee", "Ritter"]},
    {"number": 22, "project_id": "06367 A-C, H", "project_name": "Riverport Tap: Construct Tap", "project_type": "LINE", "voltages": ["230000"], "locations": ["Okatie", "Riverport"]},
    {"number": 23, "project_id": "06367 D-G", "project_name": "Jasper - Okatie 230 kV #2: Construct", "project_type": "LINE", "voltages": ["230000"], "locations": ["Jasper", "Okatie"]},
    {"number": 24, "project_id": "06371 D", "project_name": "Wagener 115kV Tap: Construct Tap", "project_type": "MULTI_LINE", "voltages": ["115000"], "locations": ["Edmund", "Owens Corning", "Wagener"]},
    {"number": 25, "project_id": "06372 A", "project_name": "Church Creek - Ritter 230kV - Replace 38 Large Angles and Dead Ends", "project_type": "LINE", "voltages": ["230000"], "locations": ["Church Creek", "Ritter"]},
    {"number": 26, "project_id": "06810 F", "project_name": "VCS2-Ward 230kV: Rebuild Line", "project_type": "LINE", "voltages": ["230000"], "locations": ["VCS2", "Ward"]},
    {"number": 27, "project_id": "06810 G", "project_name": "Goose Creek Reservoir: Rebuild Transmission Line Crossings", "project_type": "MULTI_LINE", "voltages": ["230000", "115000"], "locations": ["Williams", "Goose Creek", "Faber Place"]},
    {"number": 28, "project_id": "06810 H", "project_name": "Summerville 115kV Loop: Rebuild", "project_type": "LINE", "voltages": ["115000"], "locations": ["Summerville"]},
    {"number": 29, "project_id": "6809 M", "project_name": "St George - Sumter 230kV Tie: Rebuild Line from Santee Substation - Duke/Progress Energy Tie", "project_type": "MULTI_LINE", "voltages": ["230000"], "locations": ["St George", "Sumter", "Santee"]},
    {"number": 30, "project_id": "5392 A-C", "project_name": "Coit - Gills Creek 115kV: Construct", "project_type": "LINE", "voltages": ["115000"], "locations": ["Coit", "Gills Creek"]},
    {"number": 31, "project_id": "6810 A", "project_name": "Hooks - Thurmond 115kV Tie: Rebuild", "project_type": "LINE", "voltages": ["115000"], "locations": ["Hooks", "Thurmond"]},
    {"number": 32, "project_id": "6809 N", "project_name": "Batesburg - Saluda County 115kV: Rebuild", "project_type": "LINE", "voltages": ["115000"], "locations": ["Batesburg", "Saluda County"]},
    {"number": 33, "project_id": "6853 B-F", "project_name": "Scout 230 kV Sub and Fold-in: Construct", "project_type": "BOTH", "voltages": ["230000"], "locations": ["Scout", "VCS1", "Killian"]},
    {"number": 34, "project_id": "6859", "project_name": "Dawson 230kV Sub and Fold-in: Construct and Rebuild", "project_type": "BOTH", "voltages": ["230000"], "locations": ["Dawson", "Canadys", "Church Creek", "Faber Place"]},
    {"number": 35, "project_id": "6852", "project_name": "Urquhart - Toolebeck 115kV line: Rebuild", "project_type": "LINE", "voltages": ["115000"], "locations": ["Urquhart", "Toolebeck"]},
    {"number": 36, "project_id": "6388 A", "project_name": "Williams-Summerville 230kV: Upgrade to SPDC B1272 ACSR", "project_type": "MULTI_LINE", "voltages": ["230000"], "locations": ["Ladson Junction", "Williams", "Summerville"]},
    {"number": 37, "project_id": "0147 C, K", "project_name": "Cainhoy 115 kV Tap: Construct", "project_type": "LINE", "voltages": ["115000"], "locations": ["Cainhoy", "Clements Ferry"]},
    {"number": 38, "project_id": "0147 B, J", "project_name": "Jack Primus 115 kV Tap: Construct", "project_type": "LINE", "voltages": ["115000"], "locations": ["Jack Primus", "Clements Ferry"]},
    {"number": 39, "project_id": "6847 A-B, D-H", "project_name": "Church Creek - Faber Place - Charleston Transmission: Add 230kV Line", "project_type": "MULTI_LINE", "voltages": ["230000", "115000"], "locations": ["Church Creek", "Faber Place", "Charleston Transmission"]},
    {"number": 40, "project_id": "6846 A", "project_name": "Eastover - Sumter 115kV DEP Tie: Rebuild with 1272 ACSR", "project_type": "LINE", "voltages": ["115000"], "locations": ["Eastover", "Sumter"]},
    {"number": 41, "project_id": "6810 U", "project_name": "Cameron Jct - Elloree 46 kV Rebuild", "project_type": "LINE", "voltages": ["46000"], "locations": ["Cameron Junction", "Elloree"]},
    {"number": 42, "project_id": "6810 J", "project_name": "Elloree - Santee City 46 kV: Rebuild", "project_type": "LINE", "voltages": ["46000"], "locations": ["Elloree", "Santee City"]},
    {"number": 43, "project_id": "6810 O", "project_name": "Urquhart - Aiken PSA 46 kV: Rebuild", "project_type": "LINE", "voltages": ["46000"], "locations": ["Urquhart", "Aiken PSA"]},
    {"number": 44, "project_id": "6810 T", "project_name": "Cameron Jct - Cameron - St Matthews 46 kV Rebuild", "project_type": "MULTI_LINE", "voltages": ["46000"], "locations": ["Cameron Junction", "Cameron", "St Matthews"]},
]


def load_projects_csv(filename):
    # Reads a parser CSV such as data/processed/georgia_power_projects.csv.
    # csv keeps every value a string, so IDs like "09662" keep their
    # leading zero and voltages stay "115000" for voltage matching.
    projects = []
    with open(filename, newline="", encoding="utf-8-sig") as file:
        for number, row in enumerate(csv.DictReader(file), start=1):
            projects.append({
                "number": number,
                "project_id": row["project_id"],
                "utility": row["utility"],
                "state": row["state"],
                "project_name": row["project_name"],
                "project_type": row["project_type"],
                "voltages": [v for v in (row["voltage_1"], row["voltage_2"]) if v],
                "locations": [l for l in (row["location_1"], row["location_2"], row["location_3"]) if l],
            })
    return projects


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}


def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as file:
        json.dump(cache, file, indent=2)


CACHE = load_cache()

GENERIC_WORDS = {
    "sub", "substation", "transmission", "station",
    "switching", "distribution", "tap", "line",
}


def normalize_name(text):
    if not text:
        return ""
    text = text.lower()
    text = text.replace("&", " and ")
    text = re.sub(r"\bft\b", "fort", text)
    text = re.sub(r"\bst\b", "saint", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    words = [word for word in text.split() if word not in GENERIC_WORDS]
    return " ".join(words)


def name_match_score(target_name, candidate_name):
    target = normalize_name(target_name)
    candidate = normalize_name(candidate_name)

    if not target or not candidate:
        return 0, None
    if target == candidate:
        return 6, "Exact/normalized name match"
    if target in candidate or candidate in target:
        return 5, "Strong partial name match"

    target_words = set(target.split())
    candidate_words = set(candidate.split())
    if not target_words or not candidate_words:
        return 0, None

    similarity = len(target_words & candidate_words) / len(target_words | candidate_words)
    if similarity >= 0.67:
        return 4, "Strong word overlap"
    if similarity >= 0.40:
        return 2, "Partial word overlap"
    return 0, None


def operator_matches(operator):
    operator_lower = (operator or "").lower()
    return any(alias in operator_lower for alias in OPERATOR_ALIASES)


def extract_voltage_numbers(voltage_text):
    return set(re.findall(r"\d+", str(voltage_text or "")))


def voltage_match_count(expected_voltages, candidate_voltage):
    candidate_numbers = extract_voltage_numbers(candidate_voltage)
    return sum(1 for voltage in expected_voltages if str(voltage) in candidate_numbers)


def haversine_miles(lat1, lon1, lat2, lon2):
    r = 3958.8
    lat1, lon1, lat2, lon2 = map(math.radians, map(float, [lat1, lon1, lat2, lon2]))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def geocode_general_location(location_name):
    query = f"{location_name}, {STATE}, {COUNTRY}"
    cache_key = f"nominatim::{query}"

    if cache_key in CACHE:
        return CACHE[cache_key]

    print(f"    Nominatim: {query}")

    params = {
        "q": query,
        "format": "jsonv2",
        "countrycodes": "us",
        "limit": 1,
    }
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(
            NOMINATIM_URL,
            params=params,
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            result = None
        else:
            result = {
                "lat": float(data[0]["lat"]),
                "lon": float(data[0]["lon"]),
                "display_name": data[0].get("display_name", ""),
            }

    except requests.RequestException as error:
        print(f"    Nominatim error: {error}")
        result = None

    CACHE[cache_key] = result
    save_cache(CACHE)

    # Keep public Nominatim usage at <= 1 request/second.
    time.sleep(NOMINATIM_DELAY_SECONDS)
    return result


def search_nearby_substations(latitude, longitude):
    query = f"""
[out:json][timeout:25];
(
  node["power"="substation"](around:{SEARCH_RADIUS_METERS},{latitude},{longitude});
  way["power"="substation"](around:{SEARCH_RADIUS_METERS},{latitude},{longitude});
  relation["power"="substation"](around:{SEARCH_RADIUS_METERS},{latitude},{longitude});
);
out center tags;
"""

    body = urlencode({"data": query})
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": USER_AGENT,
    }

    for server in OVERPASS_SERVERS:
        try:
            response = requests.post(
                server,
                data=body,
                headers=headers,
                timeout=45,
            )

            if response.status_code == 200:
                time.sleep(OVERPASS_DELAY_SECONDS)
                return response.json().get("elements", [])

            print(f"    Overpass returned {response.status_code}: {server}")

        except (requests.RequestException, ValueError) as error:
            print(f"    Overpass failed ({server}): {error}")

    return []


def get_osm_coordinates(element):
    if element.get("type") == "node":
        return element.get("lat"), element.get("lon")
    center = element.get("center", {})
    return center.get("lat"), center.get("lon")


def score_candidate(target_name, expected_voltages, seed_lat, seed_lon, element):
    tags = element.get("tags", {})
    candidate_name = tags.get("name", "")
    operator = tags.get("operator", "")
    voltage = tags.get("voltage", "")
    candidate_lat, candidate_lon = get_osm_coordinates(element)

    if candidate_lat is None or candidate_lon is None:
        return None

    score = 0.0
    reasons = []

    points, reason = name_match_score(target_name, candidate_name)
    score += points
    if reason:
        reasons.append(reason)

    if operator_matches(operator):
        score += 2
        reasons.append("Operator matches Dominion/DESC")

    matches = voltage_match_count(expected_voltages, voltage)
    if matches:
        score += min(matches, 2)
        reasons.append(f"{matches} expected voltage match(es)")

    distance = haversine_miles(seed_lat, seed_lon, candidate_lat, candidate_lon)
    if distance <= 2:
        score += 2
        reasons.append("Within 2 miles of seed location")
    elif distance <= 8:
        score += 1
        reasons.append("Within 8 miles of seed location")
    elif distance <= 15:
        score += 0.5
        reasons.append("Within 15 miles of seed location")

    return {
        "matched_name": candidate_name or "Unnamed",
        "matched_operator": operator or "Unknown",
        "matched_voltage": voltage or "Unknown",
        "latitude": candidate_lat,
        "longitude": candidate_lon,
        "osm_id": element.get("id"),
        "osm_type": element.get("type"),
        "distance_from_seed_miles": round(distance, 2),
        "score": round(score, 2),
        "reasons": reasons,
    }


def confidence_from_candidate(candidate):
    if candidate is None:
        return "LOW"

    score = candidate.get("score", 0)
    if candidate.get("matched_name") == "Unnamed":
        return "MEDIUM" if score >= 5 else "LOW"
    if score >= 8:
        return "HIGH"
    if score >= 5:
        return "MEDIUM"
    return "LOW"


def locate_project_location(project, location_name, role_number):
    print(f"\n  Location {role_number}: {location_name}")
    seed = geocode_general_location(location_name)

    if seed is None:
        return {
            "project_number": project["number"],
            "project_id": project["project_id"],
            "utility": project["utility"],
            "state": project["state"],
            "project_name": project["project_name"],
            "project_type": project["project_type"],
            "location_role": f"location_{role_number}",
            "target_location": location_name,
            "expected_voltages": ";".join(project["voltages"]),
            "seed_latitude": "",
            "seed_longitude": "",
            "seed_display_name": "",
            "matched_name": "",
            "matched_operator": "",
            "matched_voltage": "",
            "latitude": "",
            "longitude": "",
            "osm_id": "",
            "osm_type": "",
            "distance_from_seed_miles": "",
            "match_score": 0,
            "confidence": "LOW",
            "source": "No match",
            "reasons": "Nominatim could not find general location",
        }

    print(f"    Seed: {seed['lat']}, {seed['lon']}")
    substations = search_nearby_substations(seed["lat"], seed["lon"])
    print(f"    Nearby substations: {len(substations)}")

    candidates = []
    for element in substations:
        scored = score_candidate(
            location_name,
            project["voltages"],
            seed["lat"],
            seed["lon"],
            element,
        )
        if scored:
            candidates.append(scored)

    candidates.sort(key=lambda item: item["score"], reverse=True)

    if candidates:
        best = candidates[0]
        confidence = confidence_from_candidate(best)

        print(
            f"    Best: {best['matched_name']} | "
            f"score {best['score']} | {confidence}"
        )

        return {
            "project_number": project["number"],
            "project_id": project["project_id"],
            "utility": project["utility"],
            "state": project["state"],
            "project_name": project["project_name"],
            "project_type": project["project_type"],
            "location_role": f"location_{role_number}",
            "target_location": location_name,
            "expected_voltages": ";".join(project["voltages"]),
            "seed_latitude": seed["lat"],
            "seed_longitude": seed["lon"],
            "seed_display_name": seed["display_name"],
            "matched_name": best["matched_name"],
            "matched_operator": best["matched_operator"],
            "matched_voltage": best["matched_voltage"],
            "latitude": best["latitude"],
            "longitude": best["longitude"],
            "osm_id": best["osm_id"],
            "osm_type": best["osm_type"],
            "distance_from_seed_miles": best["distance_from_seed_miles"],
            "match_score": best["score"],
            "confidence": confidence,
            "source": "OpenStreetMap / Overpass",
            "reasons": "; ".join(best["reasons"]),
        }

    # If no OSM power asset is found, keep the general place only as a
    # LOW-confidence fallback. It is NOT treated as a verified substation.
    print("    No OSM substation match; using LOW-confidence general-location fallback.")

    return {
        "project_number": project["number"],
        "project_id": project["project_id"],
        "utility": project["utility"],
        "state": project["state"],
        "project_name": project["project_name"],
        "project_type": project["project_type"],
        "location_role": f"location_{role_number}",
        "target_location": location_name,
        "expected_voltages": ";".join(project["voltages"]),
        "seed_latitude": seed["lat"],
        "seed_longitude": seed["lon"],
        "seed_display_name": seed["display_name"],
        "matched_name": "",
        "matched_operator": "",
        "matched_voltage": "",
        "latitude": seed["lat"],
        "longitude": seed["lon"],
        "osm_id": "",
        "osm_type": "",
        "distance_from_seed_miles": "",
        "match_score": 0,
        "confidence": "LOW",
        "source": "Nominatim general-location fallback",
        "reasons": "No nearby OSM substation candidate found",
    }


LOCATION_FIELDS = [
    "project_number", "project_id", "utility", "state",
    "project_name", "project_type",
    "location_role", "target_location", "expected_voltages",
    "seed_latitude", "seed_longitude", "seed_display_name",
    "matched_name", "matched_operator", "matched_voltage",
    "latitude", "longitude", "osm_id", "osm_type",
    "distance_from_seed_miles", "match_score", "confidence",
    "source", "reasons",
]


def write_csv(filename, rows, fields):
    with open(filename, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_project_summaries(projects, location_rows):
    by_project = {}
    for row in location_rows:
        by_project.setdefault(row["project_number"], []).append(row)

    confidence_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    summaries = []

    # Every project gets a summary row, even one with no location names,
    # so the summary joins one-to-one with the input projects.
    for project in projects:
        rows = by_project.get(project["number"], [])

        usable = [
            (float(row["latitude"]), float(row["longitude"]))
            for row in rows
            if row["latitude"] != "" and row["longitude"] != ""
        ]

        if usable:
            centroid_lat = sum(lat for lat, _ in usable) / len(usable)
            centroid_lon = sum(lon for _, lon in usable) / len(usable)
        else:
            centroid_lat = ""
            centroid_lon = ""

        overall_confidence = min(
            (row["confidence"] for row in rows),
            key=lambda value: confidence_rank.get(value, 0),
            default="LOW",
        )

        coordinates = " | ".join(
            f"{row['target_location']}: {row['latitude']},{row['longitude']} ({row['confidence']})"
            for row in rows
        )

        summaries.append({
            "project_number": project["number"],
            "project_id": project["project_id"],
            "utility": project["utility"],
            "state": project["state"],
            "project_name": project["project_name"],
            "project_type": project["project_type"],
            "expected_voltages": ";".join(project["voltages"]),
            "total_locations": len(rows),
            "located_locations": len(usable),
            "overall_confidence": overall_confidence,
            "centroid_latitude": centroid_lat,
            "centroid_longitude": centroid_lon,
            "location_coordinates": coordinates,
        })

    return summaries


SUMMARY_FIELDS = [
    "project_number", "project_id", "utility", "state",
    "project_name", "project_type",
    "expected_voltages", "total_locations", "located_locations",
    "overall_confidence", "centroid_latitude", "centroid_longitude",
    "location_coordinates",
]


def main():
    parser = argparse.ArgumentParser(description="Locate project endpoints in OpenStreetMap.")
    parser.add_argument(
        "--projects-csv",
        help="parser output CSV to locate (default: the built-in DESC list)",
    )
    parser.add_argument(
        "--output-prefix",
        default="desc",
        help="writes <prefix>_project_locations.csv, <prefix>_projects_summary.csv "
             "and <prefix>_manual_review.csv (default: desc)",
    )
    args = parser.parse_args()

    if args.projects_csv:
        projects = load_projects_csv(args.projects_csv)
    else:
        projects = [{**project, "utility": UTILITY, "state": STATE} for project in PROJECTS]

    output_locations = f"{args.output_prefix}_project_locations.csv"
    output_summary = f"{args.output_prefix}_projects_summary.csv"
    output_review = f"{args.output_prefix}_manual_review.csv"

    print("=" * 60)
    print(f"GRIDLOCK - {len(projects)} PROJECT LOCATOR")
    print("=" * 60)

    projects_to_run = projects if PROJECT_LIMIT is None else projects[:PROJECT_LIMIT]
    all_location_rows = []

    for project in projects_to_run:
        print("\n" + "=" * 60)
        print(f"PROJECT {project['number']} OF {len(projects)}")
        print(f"ID: {project['project_id']}")
        print(project["project_name"])

        for index, location_name in enumerate(project["locations"], start=1):
            row = locate_project_location(project, location_name, index)
            all_location_rows.append(row)

            # Save progress after every location.
            write_csv(output_locations, all_location_rows, LOCATION_FIELDS)

    summaries = build_project_summaries(projects_to_run, all_location_rows)
    write_csv(output_summary, summaries, SUMMARY_FIELDS)

    review_rows = [
        row for row in all_location_rows
        if row["confidence"] != "HIGH"
    ]
    write_csv(output_review, review_rows, LOCATION_FIELDS)

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)
    print(f"\nDetailed locations: {output_locations}")
    print(f"Project summaries:  {output_summary}")
    print(f"Needs review:       {output_review}")
    print("\nIMPORTANT: LOW/MEDIUM results are candidates, not verified utility coordinates.")
    print("\nMap/geocoding data: © OpenStreetMap contributors.")


if __name__ == "__main__":
    main()
