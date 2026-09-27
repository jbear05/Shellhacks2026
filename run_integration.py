import json
from dominionScript import extract_utility_projects
from integration_adapter import map_project


def load_sample_candidates():
    # Try to use cached geocode / locator output if present
    try:
        with open("gridlock_geocode_cache.json", "r", encoding="utf-8") as fh:
            cache = json.load(fh)
    except Exception:
        cache = {}

    # Construct a couple of fake locator candidates for demo
    candidates = [
        {
            "name": "Okatie",
            "operator": "Dominion",
            "voltage": "230000",
            "latitude": cache.get("nominatim::Okatie, South Carolina, USA", {}).get("lat", 32.2956335),
            "longitude": cache.get("nominatim::Okatie, South Carolina, USA", {}).get("lon", -80.9448103),
            "osm_id": 1,
            "osm_type": "node",
            "score": 8,
            "reasons": ["Exact name", "Voltage match"]
        }
    ]

    return candidates


def run():
    projects = extract_utility_projects("2024-2028-2million-and-above-project-descriptions.pdf")

    candidates = load_sample_candidates()

    mapped = []

    for p in projects:
        m = map_project(p, candidates)
        mapped.append(m)

    print(json.dumps(mapped, indent=2))


if __name__ == "__main__":
    run()
