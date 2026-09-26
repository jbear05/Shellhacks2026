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
