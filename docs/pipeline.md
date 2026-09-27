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
  |  frontend/impact.py: shared-corridor land estimate           built (section 5)
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

Built: `frontend/impact.py` estimates the land two nearby lines could save by sharing
one corridor, the brief's suggested measure of impact
([challenge.md](challenge.md#deliverables)). `frontend/analysis.py` adds its columns to
every overlap row, and the Overlaps page shows it for the focused pair.

- **Shared miles:** the shorter of the two lines' `line_miles`, the length a project's
  plan gives when it gives exactly one ([data.md](data.md)). It's an upper bound: it
  assumes the whole shorter line could run in the shared corridor. The distance between
  the two projects is not a corridor length and isn't used.
- **Easement width:** the narrower of the two lines' typical cross-country easements
  from Georgia Transmission Corporation's [Transmission Line Heights and Easement Widths
  (2017)](https://www.gatransmission.com/wp-content/uploads/2017/09/GTC_PoleHeightsFactSheet.pdf):
  100 feet at 115 kV and 230 kV, and 150 at 500 kV (the low end of each range).
  The same widths are used for DESC.
- **Acres saved:** shared miles × 5,280 × width ÷ 43,560. One corridor still needs the
  wider easement, so the narrower one is what's saved.
- **Value:** the average of the two states' 2026 farm real estate values, $4,950 an acre
  in Georgia and $4,900 in South Carolina ([USDA NASS, Land Values 2026 Summary, July
  2026, page 9](https://www.nass.usda.gov/Publications/Todays_Reports/reports/land0726.pdf#page=9)).
  Farm real estate includes buildings, so this is a proxy rather than an easement price.
  A project's state is its `County / Region` when that is one of those states, otherwise
  its utility's. Both reference PDFs were checked on 2026-09-27.

A pair gets no estimate, and `impact_explanation` says why, when either project isn't
line work (`LINE`, `MULTI_LINE` or `BOTH`), has no single `line_miles`, has a voltage
without a width (46 kV), or has no state value. On 2026-09-27, 25 of the demo's 73 pairs
had an estimate, from about $6,000 to $531,000. Missing-input reasons can overlap:
35 pairs lacked a line length, 14 included non-line work and 5 included 46 kV work.

Not built: construction cost. Every Georgia Power cost is redacted. Dollars per mile
could come from the 19 DESC projects with a `line_miles` value
(`cost_total / line_miles`), applied to Georgia's `line_miles`. Three DESC totals don't
equal the sum of their years; see
[sources/dominion-pdf.md](sources/dominion-pdf.md#cost-table).

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
  Streamlit tests. `frontend/ui.py` draws the shared header. The map's basemap (Carto)
  needs internet; nothing else does.
- **Theme and fonts:** Streamlit reads `.streamlit/config.toml` from the directory it's
  launched in, and serves the `static/` folder next to the entry script at
  `app/static/`. So the root launch uses `.streamlit/config.toml` and `static/`, and
  `cd frontend` then `streamlit run app.py` uses `frontend/.streamlit/config.toml`
  (Nellie's colors) and `frontend/static/`. Both folders hold the same two fonts, and a
  font's `url` must start with `app/static/`: a plain `static/` URL returns the page's
  HTML and the font silently falls back to Source Sans.
- **Overview** (`0_Overview.py`): "Explore the real-data demo" loads
  `load_demo_projects()` (DESC and Georgia Power's GPC and SAV rows) and opens the
  Overlaps page.
- **Project Setup** (`1_Project_Setup.py`) loads projects from one of four sources:
  the saved plans (the same demo data), the two organizer PDFs (`pdf_import.py`,
  recognized by hash and loaded from the committed parser tables; any other PDF is
  rejected), CSV/XLSX tables per utility
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
  it and shows both projects' sources, location evidence and the shared-corridor estimate
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
