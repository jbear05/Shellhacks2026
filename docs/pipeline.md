# Pipeline

How data gets from the source PDFs to the map. This file describes each stage's design;
whether it has been run, and what's left, is in [status.md](status.md).

```text
Source PDFs (Sperry-Tech-Challenge/Project Listings/)
  |  parsers/georgia_power.py, dominionScript.py                  built
  |  parsers/ai_parser (any PDF, checked against the page text)   built
  v
data/processed/georgia_power_projects.csv, dominion_projects.csv  committed
data/processed/ai/<prefix>_projects.csv                           saved runs; current code needs fixes
  |  gridlock_desc_locator.py                                     built
  |  + data/overrides/location_overrides.csv (hand-checked)       built
  v
data/processed/<prefix>_project_locations.csv, _projects_summary.csv, _manual_review.csv
  |  overlap finder                                               planned
  v
overlap table and ranked list
  |  Streamlit UI (origin/NA)                                     on a branch
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

## 4. Overlaps (planned)

- **Distance:** haversine between the two project centers. Under 25 miles makes an
  overlap row. The organizers take the midpoint of two named points, or the one point
  that was located ([challenge.md](challenge.md#the-organizers-method)). The
  Geolocator's centroid is the mean of all of a project's located points instead, up
  to 4 for DESC, including LOW fallbacks. Decide which to use: the organizers' rule
  needs `<prefix>_project_locations.csv` (one row per point, with `location_role`),
  not the summary. Carry each project's `overall_confidence` into the overlap row so
  reviewers can see which centers are only a town or county.
- **`time_gap`:** absolute days between the two `in_service_date`s.
- **Build windows:** [`start_date`, `in_service_date`]. A blank DESC `start_date`
  means work began before 2024, so treat it as open-ended. Don't assume
  `start_date <= in_service_date` (TEAMS 20248), and add a warning for that case to
  `find_inconsistencies` in `parsers/georgia_power.py`.
- **Which Georgia projects:** the CSV has every sponsor. The organizers' example counts
  SAV projects as Georgia Power, so "Georgia Power" is GPC and SAV. GTC, MEAG and DU
  projects are other utilities; including them needs a decision.
- **Where to look:** probably only Georgia projects around Savannah and Augusta can be
  within 25 miles of a DESC project.
- **Ranking:** the brief doesn't define it. It says distance is the primary signal
  and timeline the secondary one. `ranking.py` implements a simple 0-3 point model
  for five categories: geographic distance, timeline overlap, days apart, power
  voltage and project type. Higher totals rank first; distance is the first tie-break.
  Missing voltage or type data scores zero and is named in `ranking_reason`. The CLI
  can enrich overlap rows from project CSVs keyed on (`utility`, `project_id`).
- **Output:** the two sheets of `Projects_Overlaps.xlsx`
  ([challenge.md](challenge.md#target-tables-projects_overlapsxlsx)).
- **Check it** against the organizers' 6 example overlaps
  ([challenge.md](challenge.md#the-organizers-example-answers)). Their distances are
  reproducible to the hundredth, which makes them a good test.

## 5. Cost estimate (bonus, planned)

Every Georgia Power cost is redacted. Work out dollars per mile from the 19 DESC
projects with a `line_miles` value (`cost_total / line_miles`) and apply it to Georgia's
`line_miles`. Three DESC totals don't equal the sum of their years; see
[sources/dominion-pdf.md](sources/dominion-pdf.md#cost-table). The brief also suggests
shared land (right-of-way) as a measure of impact.

## 6. UI (`origin/NA`, not merged)

A Streamlit app in `frontend/`, by teammates, as of `origin/NA` commit fb1c0c3. Its
pages are `frontend/pages/1_Project_Setup.py` to `5_Export.py`, and `frontend/ui.py`
holds the shared page layout. The entry file, `frontend/app.py`, is empty. It has its
own `frontend/requirements.txt` (streamlit, pandas, openpyxl).

- **Input:** on the setup page, the user names two utilities and uploads CSV or XLSX
  files for each (`frontend/data_loader.py`). Every row of a file is labeled with the
  utility it was uploaded under, whatever its own `utility` column says. Upload only
  Georgia Power's own projects as Georgia Power
  (`python -m parsers.georgia_power --sponsors GPC SAV --out <file>`).
- **Columns** are matched through `COLUMN_ALIASES`, ignoring case: `project_id`,
  `project_name`, `utility`, `project_type`, `state` (shown as "County / Region"),
  `in_service_date`, `latitude`/`longitude` or `lat`/`lon`, and the organizers' sheet
  columns `name_a`, `lat_a`, `lon_a`, `name_b`, `lat_b`, `lon_b`, `lat_center` and
  `lon_center` ([challenge.md](challenge.md#target-tables-projects_overlapsxlsx)). A
  sheet without a `project_name` column is skipped. When a row has no center, the
  midpoint of its two points is used.
- **Our files as they are:** the parser CSVs load, but have no coordinates. The
  Geolocator's summary has `centroid_latitude` and `centroid_longitude`, which aren't
  in the alias list. Something needs to write a per-project table the UI can map, and
  the organizers' `projects` sheet layout is the natural choice.
- **IDs:** files are read with pandas defaults, so `09662` becomes `9662` (see
  [data.md](data.md#reading-the-csvs)). Duplicate `Project ID`s are dropped across both
  utilities together, not per utility.
- **Overlaps page** (`4_Overlaps.py`): haversine between the `Latitude`/`Longitude` of
  every pair, kept when within the setup page's threshold (default 25 miles), with the
  absolute gap in days between in-service dates.
- `frontend/test_data/` holds synthetic projects and expected pairs for testing the
  UI. None of it comes from the PDFs.
