# Gridlock (ShellHacks 2026, Sperry Tech challenge)

Flag where Dominion Energy South Carolina and Georgia Power plan transmission work
within 25 miles of each other and in overlapping build windows. The challenge brief,
guide and source PDFs are in `Sperry-Tech-Challenge/`.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Georgia Power parser

```bash
python -m parsers.georgia_power                      # all sponsors
python -m parsers.georgia_power --sponsors GPC SAV   # Georgia Power's own projects only
```

Writes `data/processed/georgia_power_projects.csv`, one row per project in the
Ten-Year Plan inside `2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf`. It joins two parts of
the plan on TEAMS number:

- Table 2 (project list): name, zone, plan year, need date, sponsor.
- Section IV detail pages: start date, scope description, change since the last plan.

The run stops with an error if the PDF's structure no longer matches what the parser
expects (for example, row counts that don't reconcile). Problems in the source data
itself, such as 3 projects whose need date differs between Table 2 and their detail
page, are logged as warnings.

Column notes:

- `project_id` is the TEAMS number. `in_service_date` is the Table 2 need date.
- `sponsor` is GPC, SAV (Georgia Power's Savannah area), GTC, MEAG or DU; `utility`
  spells it out.
- `location_*`, `project_type` and `voltage_*` are derived from the title with
  heuristics. They use the Geolocator's `projects.csv` conventions (voltages in volts),
  but check them before geocoding.
- `owner_tags` lists owners named in the title: `USA` (federal), `APC` (Alabama Power),
  `FPL`, or `SAV`/`GPC` (Georgia Power itself). An OpenStreetMap search filtered on
  Georgia Power as operator may miss endpoints tagged with another owner.
- `line_miles` is set only when the description gives exactly one mileage;
  `miles_mentioned` lists every mileage it gives.

## Tests

```bash
pytest                 # everything; parses the real PDF once (about 12 s)
pytest -m "not slow"   # unit tests only (under a second)
```

## Geolocator

```bash
python gridlock_desc_locator.py   # the 44 DESC projects listed in the script
python gridlock_desc_locator.py --projects-csv data/processed/georgia_power_projects.csv --output-prefix georgia_power
```

Finds coordinates for each project's location names. Nominatim gives a general place,
then Overpass looks for OpenStreetMap substations within 25 km of it, scored on name,
operator, voltage and distance. It writes three files:

- `<prefix>_project_locations.csv`: one row per location.
- `<prefix>_projects_summary.csv`: one row per project, with the average of its points.
- `<prefix>_manual_review.csv`: every location not rated HIGH.

Notes:

- Join the outputs to a parser CSV on `utility` and `project_id`. `location_role`
  (`location_1` to `location_3`) names the parser column a location came from. Read
  IDs as text (pandas: `dtype=str, keep_default_na=False`): some TEAMS numbers start
  with 0.
- LOW rows are often just the town or county Nominatim found, and the project's
  average includes them. Check `overall_confidence` before trusting a project's point.
- Nominatim and Overpass results are cached in `gridlock_geocode_cache.json`, so a
  re-run only repeats failed requests. Overpass often returns 429 or 504 errors; those
  rows say "Overpass request failed; re-run to retry".
- Each location is searched in its project's state, except those listed in
  `LOCATION_STATE_OVERRIDES` (Purrysburg, SC, for Georgia's 20277).
