---
name: geocode
description: Run the Geolocator (gridlock_desc_locator.py) on the DESC list or a parser CSV, retry failed Nominatim and Overpass requests, and summarize what needs manual review. Use when asked to geocode, locate projects, find or refresh coordinates, or re-run the locator.
---

# Geocode projects

The Geolocator calls public servers with strict usage policies, and a full run takes
minutes. Read docs/geolocator.md first.

## 1. Agree on the scope

Tell the user what the run will cover and roughly how long it takes, and wait for
their go-ahead:

- DESC: 101 location slots (the built-in list).
- Georgia Power: 353 location slots, 215 distinct names.
- Each name not yet in `gridlock_geocode_cache.json` costs at least 1.1 s for
  Nominatim, plus an Overpass request. Cached names cost nothing.
- For a quick test, set `PROJECT_LIMIT = 3` at the top of the script, and set it back
  to `None` afterwards.

## 2. Run from the repo root, in the background

```bash
.venv/Scripts/python gridlock_desc_locator.py
.venv/Scripts/python gridlock_desc_locator.py --projects-csv data/processed/georgia_power_projects.csv --output-prefix georgia_power
```

Don't run both at once: they share the cache file, and each would overwrite the
other's new entries. Stopping a run is safe; cached results are kept.

## 3. Retry failures

Count the rows whose `reasons` say "re-run to retry":

```bash
grep -c "re-run to retry" data/processed/<prefix>_project_locations.csv
```

Run the same command again until the count is 0 or stops going down. Overpass often
returns 429 or 504: wait a few minutes between runs rather than retrying in a loop.

A `null` Nominatim entry in the cache means "not found" and isn't retried. The first
version also cached failed requests as `null` (see docs/geolocator.md). To retry one,
remove its `nominatim::<name>, <state>, USA` key from the cache.

## 4. Summarize for the user

- The number of locations at HIGH, MEDIUM and LOW, and how many have no coordinates.
- Projects whose `overall_confidence` is LOW, and projects with no located point.
- Rows that match the known wrong lookups in docs/geolocator.md (Evans, McIntosh).
- For Georgia Power, focus on projects around Savannah and Augusta, the ones that can
  be within 25 miles of a DESC project.

## 5. Don't hand-fix the output

Corrections go in the planned overrides file (docs/pipeline.md), not in the output
CSVs. Ask the user before committing the outputs or the grown cache, and update
docs/status.md (the handoff workflow).
