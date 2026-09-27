# Pipeline

How data gets from the source PDFs to the map. This file describes each stage's design;
whether it has been run, and what's left, is in [status.md](status.md).

```text
Source PDFs (Sperry-Tech-Challenge/Project Listings/)
  |  parsers/georgia_power.py, dominionScript.py                  built
  |  parsers/ai_parser (any PDF, checked against the page text)   built
  v
data/processed/georgia_power_projects.csv, dominion_projects.csv  committed
data/processed/ai/<prefix>_projects.csv                           committed
  |  gridlock_desc_locator.py                                     built
  |  + data/overrides/location_overrides.csv (hand-checked)       built
  v
data/processed/<prefix>_project_locations.csv, _projects_summary.csv, _manual_review.csv
  |  frontend/project_data.py: parser rows + endpoints            built (section 4)
  |  frontend/analysis.py + ranking.py: overlap finder            built (section 4)
  v
ranked overlap table
  |  Streamlit UI (frontend/)                                     committed pages don't call it yet (section 6)
  v
interactive map
```

## 1. Parse

Each parser reads one PDF and writes one CSV row per project, with the columns
described in [data.md](data.md). How each PDF is laid out, and how the parser copes, is
in [sources/](sources/).

- **Georgia Power** (`python -m parsers.georgia_power`) joins Table 2 to the detail
  pages on TEAMS number. It also guesses `location_1..3`, `project_type` and
  `voltage_1..2` from the title.
- **DESC** (`python dominionScript.py`) reads one page per project. It doesn't guess
  locations: they come from the Geolocator's hand-typed `PROJECTS` list, which also
  has endpoints named only in the descriptions (Blue Circle, Owens Corning). That's why
  the DESC CSV can't be passed to the Geolocator's `--projects-csv`. Run the Geolocator
  without it, and join its output to the CSV on (`utility`, `project_id`).

Both parsers stop with an error and write nothing if the PDF's layout no longer
matches what they expect. Problems in the source data are logged as warnings.

- **Any other PDF** (`python -m parsers.ai_parser`): Claude copies each project's values with the text and page they came from, and
  Python checks each one against the page before keeping it. It writes
  `data/processed/ai/<prefix>_projects.csv` with the Georgia parser CSV's shared
  columns and a `utility` per project, so it can go to the Geolocator's `--projects-csv`, and its eval scores it against the
  two parsers above. See [ai-parser.md](ai-parser.md).

## 2. Locate

`gridlock_desc_locator.py` turns each location name into coordinates and a confidence,
then averages each project's points into a center. How it searches and scores is in
[geolocator.md](geolocator.md). Its three output files are in [data.md](data.md).

## 3. Manual overrides

**Locations (built):** `data/overrides/location_overrides.csv` gives a checked point
for a location name the Geolocator gets wrong, or removes a wrong point when the real
one is unknown. The Geolocator applies it in place of the search, so its outputs
already include the fixes. Every row cites an OSM element or the PDF text. How it works
and how to add a row: [geolocator.md](geolocator.md#overrides).

**Not covered yet:**

- Georgia rows with no location name (`UNKNOWN`): the overrides match location names,
  so a project without one can't get a point. Neither of the two is near South
  Carolina; see [data.md](data.md#dataprocessedgeorgia_power_projectscsv).
- Other guessed parser columns, such as `project_type` and the voltages.

## 4. Overlaps

Built on `codex/finish-gridlock`: `frontend/project_data.py` builds the project table,
and `frontend/analysis.py` finds the pairs and ranks them. How centers, confidence,
distances and ranking work is in [app.md](app.md); the current results are in
[status.md](status.md#overlap-candidates).

- **Input:** the parser CSVs have the dates, and the Geolocator's
  `<prefix>_project_locations.csv` has the points, so the two are joined on (`utility`,
  `project_id`). DESC's `project_type` and voltages come from the Geolocator's list too,
  since the DESC CSV has neither. The Geolocator's summary isn't used: it has no dates,
  and its centroid is the mean of all of a project's located points (up to 4 for DESC,
  LOW fallbacks included), where the organizers take the midpoint of two named points
  ([challenge.md](challenge.md#the-organizers-method)).
- **Build windows:** [`start_date`, `in_service_date`]. A blank DESC `start_date`
  means work began before 2024, so it's open-ended. Don't assume
  `start_date <= in_service_date` (TEAMS 20248): the UI flags it, but
  `find_inconsistencies` in `parsers/georgia_power.py` doesn't warn yet.
- **Which Georgia projects:** "Georgia Power" is GPC and SAV, the rows whose `utility`
  is `Georgia Power` (138 of 208). The organizers' example counts SAV projects as
  Georgia Power. GTC, MEAG and DU projects are other utilities and are left out of the
  demo.
- **Ranking:** the brief doesn't define it. It says distance is the primary signal
  and timeline the secondary one. `ranking.py` scores five categories 0-3 points each:
  geographic distance, timeline overlap, days apart, power voltage and project type.
  Missing voltage or type data scores zero and is named in `ranking_reason`. In `score`
  mode higher totals rank first, with distance as the first tie-break. In
  `distance_first` mode, the UI's default, distance bands come first
  ([app.md](app.md#overlaps-and-ranking)). The CLI can enrich overlap rows from project
  CSVs keyed on (`utility`, `project_id`).
- **Output:** one row per pair (`RESULT_COLUMNS` in `frontend/analysis.py`). It holds
  the organizers' `overlaps` columns under other names (`distance_miles`, `days_apart`),
  plus both projects' details and the scores. Nothing writes their `.xlsx` layout
  ([challenge.md](challenge.md#target-tables-projects_overlapsxlsx)).
- **Check:** `tests/test_overlaps.py` reproduces the organizers' 6 example distances to
  the hundredth from the sheet's coordinates, then checks the same pairs with ours
  ([challenge.md](challenge.md#the-organizers-example-answers)).

## 5. Cost estimate (bonus, planned)

Every Georgia Power cost is redacted. Work out dollars per mile from the 19 DESC
projects with a `line_miles` value (`cost_total / line_miles`) and apply it to Georgia's
`line_miles`. Three DESC totals don't equal the sum of their years; see
[sources/dominion-pdf.md](sources/dominion-pdf.md#cost-table). The brief also suggests
shared land (right-of-way) as a measure of impact.

## 6. UI (`frontend/`)

A Streamlit app in `frontend/`, by teammates. Nellie merged `origin/NA` (e9e14cc) into
`main` on 2026-09-26. Its pages are `frontend/pages/1_Project_Setup.py` to
`5_Export.py`, and `frontend/ui.py` holds the shared page layout. The entry file,
`frontend/app.py`, is empty. Its packages are in `frontend/requirements.txt`
(streamlit, pandas, openpyxl, pydeck), which `requirements-dev.txt` doesn't include, so
the root `.venv` can't run it. Nobody has opened it in a browser in an agent session
yet. AaxHamm3r's plan for connecting it to the parsers, the Geolocator and `ranking.py`
is in [frontend-backend-integration-guide.md](frontend-backend-integration-guide.md).
On `codex/finish-gridlock`, `frontend/data_loader.py` was reworked and
`frontend/project_data.py`, `analysis.py` and `pdf_import.py` were added
([app.md](app.md)), but the pages described here don't call those three.

- **Input:** on the setup page, the user names two utilities and uploads CSV or XLSX
  files for each (`frontend/data_loader.py`). A row's own `utility` is kept; the
  utility it was uploaded under only fills blanks ([app.md](app.md#project-data)). To
  compare DESC with Georgia Power alone, upload only the GPC and SAV rows
  (`python -m parsers.georgia_power --sponsors GPC SAV --out <file>`).
- **Columns** are matched through `COLUMN_ALIASES`, ignoring case: our parser and
  Geolocator column names (including `centroid_latitude`, `location_1_lat` and
  `overall_confidence`), the Duke test file's `center_lat` and `center_lon`, and the
  organizers' sheet columns `name_a`, `lat_a`, `lon_a`, `name_b`, `lat_b`, `lon_b`,
  `lat_center` and `lon_center`
  ([challenge.md](challenge.md#target-tables-projects_overlapsxlsx)). `state` is shown
  as "County / Region". A sheet without a `project_name` or `name` column is skipped.
  `prepare_projects` recomputes each center from the two points
  ([app.md](app.md#centers-and-confidence)).
- **Our files as they are** (checked with `_normalize_projects`): the parser CSVs load
  with dates but no centers. The Geolocator's summaries give 43 of 44 DESC and 194 of
  208 Georgia rows a center, but they have no dates. The Duke test file gets all 100
  centers, and the DESC test file none. `load_demo_projects()` in
  `frontend/project_data.py` joins the parser CSVs to the points, which gives both
  ([4. Overlaps](#4-overlaps)).
- **IDs** are read as text. A duplicate (`Utility`, `Project ID`) stops the import, and
  the same ID under two utilities is allowed ([app.md](app.md#project-data)).
- **Overlaps page** (`4_Overlaps.py`): haversine between the `Latitude`/`Longitude` of
  every pair, kept when within the setup page's threshold (default 25 miles), with the
  absolute gap in days between in-service dates. The pairs, with their IDs, types,
  start dates and `Voltage 1`, are ranked by `frontend/ranking.py`: a separate, shorter
  copy of the root `ranking.py` with the same five scores but no project-CSV lookup.
  A change to one doesn't reach the other. `frontend/analysis.py` does the same job
  with the root `ranking.py`, but this page doesn't call it.
- **Map and review gaps (code review, 2026-09-26):** the overlaps map draws a
  threshold-radius circle around every mapped project, rather than highlighting
  computed pairs. Two 25-mile circles can intersect with centers 50 miles apart,
  so the caption's claim that intersecting circles identify matches is misleading.
  Draw the actual qualifying pairs or highlight their projects. Rows marked
  `Excluded` are still used by the pair loop. The displayed/exported overlap table
  drops project IDs, confidence, total scores and ranking reasons; preserve these
  for traceability. These findings were checked in code, not in a browser session.
- `frontend/test_data/` holds synthetic projects and expected pairs for testing the
  UI. None of it comes from the PDFs.
