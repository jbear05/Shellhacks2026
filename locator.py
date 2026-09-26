import requests
from urllib.parse import urlencode


# ==========================================================
# 1. WHAT ARE WE LOOKING FOR?
# ==========================================================

project_name = "Okatie, South Carolina"

# The important facility name
target_name = "Okatie"

# Voltages we expect based on the utility document
target_voltages = [
    "230000",
    "115000"
]

# Different names OpenStreetMap might use for Dominion
target_operator_words = [
    "Dominion",
    "DESC",
    "SCE&G",
    "South Carolina Electric"
]


print("==========================================")
print("GRIDLOCK PROJECT LOCATOR")
print("==========================================")

print("\nSearching for general location:")
print(project_name)


# ==========================================================
# 2. FIND THE GENERAL AREA USING NOMINATIM
# ==========================================================

nominatim_url = "https://nominatim.openstreetmap.org/search"

nominatim_params = {
    "q": project_name,
    "format": "jsonv2",
    "countrycodes": "us",
    "limit": 1
}

headers = {
    "User-Agent": "GridLock-Hackathon/1.0"
}

try:

    response = requests.get(
        nominatim_url,
        params=nominatim_params,
        headers=headers,
        timeout=15
    )

    response.raise_for_status()

    location_data = response.json()

except Exception as error:

    print("\nNominatim search failed.")
    print(error)
    exit()


# ==========================================================
# 3. MAKE SURE NOMINATIM FOUND SOMETHING
# ==========================================================

if not location_data:

    print("\nCould not find the general location.")
    exit()


latitude = location_data[0]["lat"]
longitude = location_data[0]["lon"]

print("\nGeneral location found!")

print("Latitude:", latitude)
print("Longitude:", longitude)


# ==========================================================
# 4. SEARCH FOR POWER SUBSTATIONS NEAR THAT LOCATION
# ==========================================================

print("\nSearching for power substations nearby...")


overpass_query = f"""
[out:json][timeout:25];

(
    node["power"="substation"]
        (around:20000,{latitude},{longitude});

    way["power"="substation"]
        (around:20000,{latitude},{longitude});
);

out center tags;
"""


# ==========================================================
# 5. SEND THE QUERY TO OVERPASS
# ==========================================================

# We can keep backup servers in case one is busy.

overpass_servers = [

    "https://overpass-api.de/api/interpreter",

    "https://overpass.kumi.systems/api/interpreter"
]


overpass_data = None


for server in overpass_servers:

    print("\nTrying Overpass server:")
    print(server)

    try:

        body = urlencode({
            "data": overpass_query
        })

        overpass_response = requests.post(

            server,

            data=body,

            headers={
                "Content-Type":
                "application/x-www-form-urlencoded",

                "User-Agent":
                "GridLock-Hackathon/1.0"
            },

            timeout=40
        )


        print(
            "Status code:",
            overpass_response.status_code
        )


        if overpass_response.status_code == 200:

            overpass_data = overpass_response.json()

            print("Overpass search worked!")

            break

        else:

            print("This server did not work.")

    except Exception as error:

        print("Server error:")
        print(error)


# ==========================================================
# 6. MAKE SURE OVERPASS WORKED
# ==========================================================

if overpass_data is None:

    print(
        "\nCould not get data from any Overpass server."
    )

    exit()


# ==========================================================
# 7. GET ALL THE SUBSTATIONS
# ==========================================================

substations = overpass_data.get(
    "elements",
    []
)


print(
    "\nNumber of substations found:",
    len(substations)
)


if not substations:

    print(
        "No mapped substations were found nearby."
    )

    exit()


# ==========================================================
# 8. SCORE EACH SUBSTATION
# ==========================================================

results = []


for substation in substations:

    tags = substation.get(
        "tags",
        {}
    )


    name = tags.get(
        "name",
        "Unnamed"
    )


    operator = tags.get(
        "operator",
        "Unknown"
    )


    voltage = tags.get(
        "voltage",
        "Unknown"
    )


    # ------------------------------------------------------
    # GET THE SUBSTATION COORDINATES
    # ------------------------------------------------------

    if substation["type"] == "node":

        sub_lat = substation.get(
            "lat"
        )

        sub_lon = substation.get(
            "lon"
        )

    else:

        center = substation.get(
            "center",
            {}
        )

        sub_lat = center.get(
            "lat"
        )

        sub_lon = center.get(
            "lon"
        )


    # ------------------------------------------------------
    # START THE SCORE
    # ------------------------------------------------------

    score = 0

    reasons = []


    # ------------------------------------------------------
    # CHECK THE NAME
    # ------------------------------------------------------

    if target_name.lower() == name.lower():

        score += 5

        reasons.append(
            "Exact name match"
        )


    elif target_name.lower() in name.lower():

        score += 4

        reasons.append(
            "Name contains target"
        )


    # ------------------------------------------------------
    # CHECK THE VOLTAGE
    # ------------------------------------------------------

    for target_voltage in target_voltages:

        if target_voltage in voltage:

            score += 1

            reasons.append(
                f"Voltage matches {target_voltage}"
            )


    # ------------------------------------------------------
    # CHECK THE OPERATOR
    # ------------------------------------------------------

    for word in target_operator_words:

        if word.lower() in operator.lower():

            score += 2

            reasons.append(
                "Operator matches Dominion"
            )

            break


    # ------------------------------------------------------
    # SAVE THIS SUBSTATION
    # ------------------------------------------------------

    results.append({

        "name":
            name,

        "operator":
            operator,

        "voltage":
            voltage,

        "latitude":
            sub_lat,

        "longitude":
            sub_lon,

        "osm_id":
            substation.get("id"),

        "osm_type":
            substation.get("type"),

        "score":
            score,

        "reasons":
            reasons
    })


# ==========================================================
# 9. SORT FROM BEST MATCH TO WORST MATCH
# ==========================================================

results.sort(

    key=lambda x: x["score"],

    reverse=True
)


# ==========================================================
# 10. SHOW ALL CANDIDATES
# ==========================================================

print("\n==========================================")
print("SUBSTATION CANDIDATES")
print("==========================================")


for result in results:

    print("\n------------------------------------------")

    print(
        "Name:",
        result["name"]
    )

    print(
        "Operator:",
        result["operator"]
    )

    print(
        "Voltage:",
        result["voltage"]
    )

    print(
        "Latitude:",
        result["latitude"]
    )

    print(
        "Longitude:",
        result["longitude"]
    )

    print(
        "OSM ID:",
        result["osm_id"]
    )

    print(
        "OSM Type:",
        result["osm_type"]
    )

    print(
        "Match Score:",
        result["score"]
    )

    print(
        "Why:",
        ", ".join(result["reasons"])
        if result["reasons"]
        else "No strong matching clues"
    )


# ==========================================================
# 11. PICK THE BEST MATCH
# ==========================================================

best_match = results[0]


print("\n\n==========================================")
print("BEST MATCH")
print("==========================================")


print(
    "Name:",
    best_match["name"]
)

print(
    "Operator:",
    best_match["operator"]
)

print(
    "Voltage:",
    best_match["voltage"]
)

print(
    "Latitude:",
    best_match["latitude"]
)

print(
    "Longitude:",
    best_match["longitude"]
)

print(
    "OSM ID:",
    best_match["osm_id"]
)

print(
    "Match Score:",
    best_match["score"]
)


# ==========================================================
# 12. GIVE THE MATCH A CONFIDENCE LEVEL
# ==========================================================

if best_match["score"] >= 7:

    confidence = "HIGH"

elif best_match["score"] >= 4:

    confidence = "MEDIUM - REVIEW"

else:

    confidence = "LOW - MANUAL REVIEW"


print(
    "Confidence:",
    confidence
)


print(
    "Why:",
    ", ".join(best_match["reasons"])
    if best_match["reasons"]
    else "No strong matching clues"
)


print("\n==========================================")
print("SEARCH COMPLETE")
print("==========================================")