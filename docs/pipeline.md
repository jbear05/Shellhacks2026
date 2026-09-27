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
  |  frontend/land_value_reference.py: land-value estimate        built (section 5)
  v
ranked overlap table
  |  Streamlit UI (frontend/)                                     built (section 6)
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

Built: `frontend/project_data.py` builds the project table, and `frontend/analysis.py`
finds the pairs and ranks them. How centers, confidence, distances and ranking work is
in [app.md](app.md); the current results are in
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

## 5. Cost and impact estimate (bonus)

Built: a land-value estimate for every pair, in `frontend/land_value_reference.py`.
`frontend/analysis.py` adds its columns to each overlap row, and the Overlaps page shows
it for the focused pair. The brief suggests shared land (right-of-way) as a measure of
impact ([challenge.md](challenge.md#deliverables)). If the two projects shared land,
the smaller footprint is the shared acres, valued at the average of the two states'
2026 farm real estate values: $4,950 an acre in Georgia and $4,900 in South Carolina,
from USDA NASS's Land Values 2026 Summary (July 2026), page 9. A project's state is its
`County / Region` when that is one of those states, otherwise its utility's.

The footprints are an assumed rule, not from the plans: 0.5 acres for a line, 1.0 for
a substation and 1.5 for both, by `ranking.py`'s project types (`MULTI_LINE` is a line,
`MULTI_SITE` both). A pair with an unknown type or state gets no estimate. With this
rule, 71 of the demo's 73 pairs come to $2,462.50 (half an acre) and the other 2 to
$4,925, so the estimate shows the method rather than ranking the pairs. A line's
right-of-way from its `line_miles` would tell them apart.

Not built: a construction cost. Every Georgia Power cost is redacted. Work out dollars
per mile from the 19 DESC projects with a `line_miles` value (`cost_total / line_miles`)
and apply it to Georgia's `line_miles`. Three DESC totals don't equal the sum of their
years; see [sources/dominion-pdf.md](sources/dominion-pdf.md#cost-table).

## 6. UI (`frontend/`)

A five-step Streamlit app, started by AaxHamm3r and Nellie (`origin/NA`, merged into
`main` at e9e14cc) and rewritten in 2fce793 to call the data and overlap modules in
section 4. How centers, confidence, PDF imports and ranking work is in
[app.md](app.md); this section covers the pages.

- **Running it:** `python -m streamlit run app.py` from the repository root. `app.py`
  calls `main()` in `frontend/app.py`, which sets the defaults (25 miles, LOW
  included, `distance_first`) and the page list. Its packages are in
  `frontend/requirements.txt` (`streamlit>=1.55,<2`, pandas, openpyxl, pydeck), which
  `requirements-dev.txt` doesn't include, so the root `.venv` can't run it or its
  Streamlit tests. The theme is in `.streamlit/config.toml`, and `frontend/ui.py` draws
  the shared header. The map's basemap (Carto) needs internet; nothing else does.
- **Overview** (`0_Overview.py`): "Explore the real-data demo" loads
  `load_demo_projects()` (DESC and Georgia Power's GPC and SAV rows) and opens the
  Overlaps page.
- **Project Setup** (`1_Project_Setup.py`) loads projects from one of four sources:
  the saved plans (the same demo data), the two organizer PDFs (`pdf_import.py`,
  recognized by hash; any other PDF is rejected), CSV/XLSX tables per utility
  (`data_loader.py`), or a snapshot ZIP (`workspace.py`). It then picks the two
  utilities and the distance threshold (1-100 miles).
- **Project Review** (`2_Project_Review.py`): edit names, types, dates, voltages and
  `Match Status`; the other columns are read-only. Rows with `Data Warnings` are listed.
- **Location Verification** (`3_Location_Confirm.py`): edit endpoints, centers,
  `Location Status` and `Confidence`. A coordinate edit keeps the original value in an
  `Original ...` column and resets the row to LOW and `Candidate`
  (`apply_location_review` in `workspace.py`). `Excluded` in either status column
  leaves the project out of the overlaps.
- **Overlap Results** (`4_Overlaps.py`): the utilities, threshold, LOW filter and
  ranking mode, the counts, a map and the ranked pairs from `frontend/analysis.py`. The
  map (`frontend/map_view.py`) draws each eligible center, and a line only between the
  projects of a computed pair. "Show distance circles" (on by default) shades a circle
  around each paired center, with a radius of half the threshold, so circles of the two
  colors overlap exactly when their centers are within it. Choosing a pair, clicking its
  line, or clicking a project (which picks its highest-ranked pair) focuses the map on
  it and shows both projects' sources, location evidence and the land-value estimate
  (section 5). What the map shows about centers is in
  [app.md](app.md#centers-and-confidence). The table keeps both project IDs, both
  confidences, the total score and `ranking_reason`, and the CSV download has every
  column in `RESULT_COLUMNS`.
- **Export** (`5_Export.py`) recalculates from the current projects and settings and
  offers three downloads: the project table, the ranked pairs, and a snapshot ZIP
  (`projects.csv`, `ranked_overlaps.csv`, `settings.json` and a README) that Project
  Setup restores. Nothing writes the organizers' `.xlsx` layout.
- **Columns** from uploads are matched through `COLUMN_ALIASES` in
  `frontend/data_loader.py`, ignoring case: our parser and Geolocator names, the Duke
  test file's `center_lat` and `center_lon`, and the organizers' sheet columns
  ([challenge.md](challenge.md#target-tables-projects_overlapsxlsx)). A sheet without a
  `project_name` or `name` column is skipped. The parser CSVs alone have dates but no
  coordinates, and the Geolocator's files have coordinates but no dates, so load our
  data through the demo or the PDFs, which join them.
- **Tests:** `tests/test_app.py` runs the pages with Streamlit's `AppTest` (demo,
  filters, reviews, exports, the same-utility guard) and pins the demo's pair counts;
  `tests/test_map_view.py` checks the map's layers; `tests/test_workspace.py` checks
  snapshots and location edits. The first two are skipped without Streamlit and pydeck.
- `frontend/test_data/` holds synthetic projects and expected pairs for testing the
  UI. None of it comes from the PDFs.
