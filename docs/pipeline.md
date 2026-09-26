# Pipeline

How data gets from the source PDFs to the map. This file describes each stage's design;
whether it has been run, and what's left, is in [status.md](status.md).

```text
Source PDFs (Sperry-Tech-Challenge/Project Listings/)
  |  parsers/georgia_power.py, dominionScript.py                  built
  v
data/processed/georgia_power_projects.csv, dominion_projects.csv  committed
  |  gridlock_desc_locator.py                                     built
  v
<prefix>_project_locations.csv, _projects_summary.csv, _manual_review.csv
  |  manual overrides                                             planned
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

## 2. Locate

`gridlock_desc_locator.py` turns each location name into coordinates and a confidence,
then averages each project's points into a center. How it searches and scores is in
[geolocator.md](geolocator.md). Its three output files are in [data.md](data.md).

## 3. Manual overrides (planned)

A file keyed by (`utility`, `project_id`), merged over the guessed columns, to fix
what the heuristics and the Geolocator get wrong:

- Georgia rows with no location (`UNKNOWN`) and customer-project names; see
  [data.md](data.md#dataprocessedgeorgia_power_projectscsv).
- Wrong lookups, which need a corrected name, state or coordinate for a single
  location; see [geolocator.md](geolocator.md#known-wrong-or-weak-lookups).

Every override should say where its value came from (a PDF page, an OSM element), so it
can be checked.

## 4. Overlaps (planned)

- **Distance:** haversine between the two project centers. Under 25 miles makes an
  overlap row. The organizers take the midpoint of two named points, or the one point
  that was located ([challenge.md](challenge.md#the-organizers-method)). The
  Geolocator's centroid is the mean of all of a project's located points instead, up
  to 4 for DESC, including LOW fallbacks. Decide which to use, and carry each project's
  `overall_confidence` into the overlap row so reviewers can see which centers are only
  a town or county.
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
  and timeline the secondary one.
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

Streamlit pages `1_Project_Setup.py` to `5_Export.py`, by a teammate. What they expect:

- `4_Overlaps.py` reads the columns `Project Name`, `Utility`, `Project Type`,
  `In-Service Date`, `Latitude` and `Longitude`. `2_Project_Review.py` adds
  `County / Region` and `Match Status`.
- It keeps rows whose `Utility` exactly equals the name typed on the setup page. Use
  `Georgia Power` (GPC and SAV; this leaves out GTC, MEAG and DU) and
  `Dominion Energy South Carolina`.
- The review page builds sample rows for now. It needs to load the merged project and
  location table.
- `streamlit` isn't in `requirements.txt` yet. `app.py` is empty on `main` and on
  `origin/NA`.
