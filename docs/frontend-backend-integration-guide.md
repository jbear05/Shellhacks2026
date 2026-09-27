# Frontend + Backend Integration Guide

## Goal

Connect the existing Streamlit frontend in `frontend/` to the backend pipeline in the repository so a user can:

1. Upload a large utility project PDF, potentially around 700 pages.
2. Parse the PDF into one normalized project row per project.
3. Resolve project locations through Nominatim and OpenStreetMap Overpass.
4. Store each matched coordinate against the project ID and project name.
5. Calculate a project center point.
   - For a two-ended transmission project, use the midpoint of the two located endpoints.
   - For a single-location project, use that one coordinate.
   - Do not silently average arbitrary low-confidence fallback points unless that is an explicit, reviewable policy.
6. Compare projects from Utility A and Utility B using a 25-mile radius or the user-selected threshold.
7. Rank qualifying pairs with the existing ranking logic.
8. Export the final ranked CSV with source, location, distance, timeline, and ranking information.

This guide describes the implementation path rather than changing the application code directly.

---

## 1. Current repository architecture

The repository already contains most of the backend pieces, but they are currently command-line tools and the Streamlit UI expects a different data shape.

### Existing backend components

| Path | Current responsibility |
|---|---|
| `parsers/georgia_power.py` | Parses the 668-page Georgia Power IRP PDF into project CSV rows. It extracts project IDs, names, dates, descriptions, locations, project types, and voltages. |
| `dominionScript.py` | Parses the Dominion Energy South Carolina project PDF into project CSV rows. |
| `parsers/ai_parser/` | Optional parser for PDFs whose layout is not supported by a handwritten parser. It uses Claude, caches replies, and writes evidence/review files. This should not be called casually at app runtime because it costs money. |
| `gridlock_desc_locator.py` | Uses Nominatim to find a general seed location, then Overpass to find nearby OSM substations and score candidates. It writes detailed location rows and project summaries. |
| `ranking.py` | Backend ranking implementation. Scores distance, timeline overlap, date gap, voltage compatibility, and project type. |
| `data/processed/` | Current command-line outputs and generated pipeline artifacts. |
| `frontend/data_loader.py` | Current Streamlit loader for CSV/XLSX uploads. It intentionally rejects PDFs because PDF extraction is not implemented there yet. |
| `frontend/pages/1_Project_Setup.py` | Collects utility names, uploaded files, and overlap threshold. |
| `frontend/pages/2_Project_Review.py` | Displays and edits normalized project rows. |
| `frontend/pages/3_Location_Confirm.py` | Displays coordinates and prepares an Overpass query, but does not currently execute the backend locator. |
| `frontend/pages/4_Overlaps.py` | Currently calculates pairwise haversine distance from `Latitude` and `Longitude`, then calls `frontend/ranking.py`. |
| `frontend/pages/5_Export.py` | Downloads project and overlap tables as CSV. |

### The main integration mismatch

The backend and frontend use different schemas:

- Backend parser columns use names such as `project_id`, `project_name`, `in_service_date`, `location_1`, and `voltage_1`.
- The frontend expects title-case columns such as `Project ID`, `Project Name`, `In-Service Date`, `Latitude`, `Longitude`, and `Voltage 1`.
- The backend locator writes `centroid_latitude` and `centroid_longitude`, while the frontend does not currently map those fields.
- The frontend currently imports CSV/XLSX only and rejects PDFs.
- The frontend's location page prepares a query but does not call `gridlock_desc_locator.py` or a shared locator function.
- The frontend's overlap page calculates centers from whatever coordinates already exist, rather than enforcing the two-endpoint midpoint rule.
- There are two ranking implementations: the root `ranking.py` and `frontend/ranking.py`. The root implementation should become the source of truth.

The safest approach is to create a shared service layer that converts backend output into the frontend's canonical schema.

---

## 2. Recommended target architecture

Use this flow:

```text
Streamlit upload
    |
    v
PDF saved to temporary/session job directory
    |
    v
Parser adapter
    |
    v
Normalized project records
    |
    v
Location resolver
  Nominatim seed -> Overpass candidates -> confidence/review rows
    |
    v
Center calculator
  endpoint midpoint or single located point
    |
    v
Canonical project table
    |
    v
Pair finder
  Utility A x Utility B + haversine threshold
    |
    v
Root ranking.py
    |
    v
Final ranked overlap CSV + review CSV + map data
```

The frontend should not shell out to a command-line process for every row. Instead, move reusable functions from the scripts into importable modules and keep the command-line scripts as thin wrappers around those modules.

Recommended new modules:

```text
backend/
  __init__.py
  models.py              # canonical records and job status
  parser_service.py      # parser selection and PDF-to-project conversion
  location_service.py    # Nominatim/Overpass adapter with cache and rate limits
  center_service.py      # endpoint midpoint and confidence policy
  overlap_service.py     # pair generation and haversine distance
  pipeline_service.py    # orchestrates the complete workflow
  export_service.py      # final CSV schemas and export
```

If adding a new top-level `backend/` package is undesirable, these modules can live under `frontend/services/`. The important rule is that the pages call Python functions instead of duplicating pipeline logic.

---

## 3. Define one canonical project schema first

Before connecting pages, define the schema that every parser, locator, overlap function, and UI page will use.

At minimum, retain these fields:

```text
Utility
Project ID
Project Name
Project Type
State
County / Region
Start Date
In-Service Date
Voltage 1
Voltage 2
Location 1 Name
Location 1 Latitude
Location 1 Longitude
Location 1 Confidence
Location 1 Source
Location 2 Name
Location 2 Latitude
Location 2 Longitude
Location 2 Confidence
Location 2 Source
Center Latitude
Center Longitude
Center Method
Overall Location Confidence
Location Status
Location Source
Verification Notes
Source File
Source Pages
Description
```

Use the source's project ID as the primary join key. Always join on:

```text
(Utility, Project ID)
```

Never join parser and geocoder output on project name. The repository documentation specifically warns that names can differ in spacing, punctuation, and capitalization, and that IDs can contain leading zeroes.

### ID handling

Read all project CSVs as text:

```python
pd.read_csv(path, dtype=str, keep_default_na=False)
```

Do not allow pandas to convert IDs such as `09662` into `9662`.

### Internal versus UI column names

Pick one representation internally. The recommended approach is:

- Use snake_case inside backend/service modules.
- Convert once to the title-case frontend schema at the service boundary.
- Do not repeatedly rename columns in each Streamlit page.

For example:

```python
{
    "utility": "Georgia Power",
    "project_id": "09662",
    "project_name": "Example Project",
    "center_latitude": 33.1234,
    "center_longitude": -81.4567,
}
```

becomes:

```python
{
    "Utility": "Georgia Power",
    "Project ID": "09662",
    "Project Name": "Example Project",
    "Latitude": 33.1234,
    "Longitude": -81.4567,
}
```

Do this conversion in one function such as `to_frontend_projects()`.

---

## 4. Handle large PDF uploads safely

A 700-page PDF should not be sent through a browser-to-backend HTTP request for every page. Streamlit can receive the file, but the pipeline should save it once and process it as a job.

### Minimum viable hackathon approach

For a local or single-user demo:

1. Accept the PDF in `1_Project_Setup.py`.
2. Copy its bytes to a temporary job directory.
3. Run the parser once when the user clicks **Start Analysis**.
4. Cache the parsed result in `st.session_state` and on disk.
5. Display progress after each pipeline stage.

Suggested session keys:

```python
st.session_state.job_id
st.session_state.job_status
st.session_state.job_error
st.session_state.raw_pdf_paths
st.session_state.parsed_projects
st.session_state.location_rows
st.session_state.projects_with_centers
st.session_state.overlaps
st.session_state.final_results
```

Example temporary layout:

```text
.data/jobs/<job_id>/
  utility_a_source.pdf
  utility_b_source.pdf
  utility_a_projects.csv
  utility_b_projects.csv
  utility_a_locations.csv
  utility_b_locations.csv
  projects_with_centers.csv
  overlaps.csv
  ranked_overlaps.csv
  manual_review.csv
```

Do not store the PDF itself in `st.session_state`; keep only the temporary file path and metadata there. `UploadedFile` objects are convenient for small files but are not a good durable job boundary for a large PDF.

### Production-ready approach

If the app will support multiple users or long-running jobs:

- Streamlit creates a job record.
- A worker process runs the parser and geocoder.
- The UI polls job status and reads checkpoint files.
- The worker writes progress after each parser page or project.
- The user can review partial results without restarting the entire job.

Possible worker technologies include a simple subprocess for a demo, or a queue such as RQ/Celery for deployment. Do not introduce a queue until the synchronous pipeline works end-to-end.

### Important timeout rule

Do not run the 700-page parse or hundreds of public API requests on every Streamlit rerun. Streamlit reruns the script whenever a widget changes. Put the pipeline behind an explicit button and guard it with a job ID or cache key.

Use a cache key based on:

```text
PDF bytes/hash + utility name + parser version + geocoder version + threshold
```

If the same file is uploaded again, reuse the previous parser output instead of parsing it again.

---

## 5. Add a parser adapter layer

The existing parsers are utility-specific. The UI should not need to know which parser implementation is being used.

Create a function with a stable interface:

```python
def parse_uploaded_pdf(
    pdf_path: Path,
    utility_name: str,
    *,
    output_dir: Path,
    parser_hint: str | None = None,
) -> pd.DataFrame:
    """Return normalized project rows for one uploaded PDF."""
```

The adapter should:

1. Choose the parser based on the selected utility or parser hint.
2. Run the handwritten parser when the PDF layout is supported.
3. Use the AI parser only when explicitly enabled and approved.
4. Convert parser-specific fields to the canonical schema.
5. Preserve source PDF page numbers and evidence where available.
6. Write a parser CSV to the job directory.
7. Raise a clear error if the PDF layout does not match the parser.

### Utility-specific parser mapping

For the current repository:

```text
Georgia Power -> parsers.georgia_power.parse_georgia_power()
Dominion Energy South Carolina -> dominionScript parser logic
Other utility -> explicit AI parser/manual adapter decision
```

The existing Georgia parser already reads the IRP's bookmarked Ten-Year Plan range instead of blindly treating every page as a project page. It joins the project list to detail pages using the TEAMS/project ID. Preserve that behavior.

The existing Dominion parser reads one project per page and leaves location/type/voltage enrichment to the location data. Preserve that behavior too.

### Do not call the paid AI parser implicitly

The repository rules state that there should be no unapproved LLM calls at app runtime. If a PDF is unsupported:

- Show a message that the utility needs a parser adapter, or
- Provide an explicit `Use AI parser` checkbox with a cost warning, confirmation, cache directory, and review output.

Every AI-extracted value should retain its page/evidence information and be reviewable before it is used for geospatial matching.

---

## 6. Make the parser output compatible with the current frontend

`frontend/data_loader.py` currently handles CSV/XLSX and already normalizes common aliases. Extend it or bypass it with the parser service so that PDF results enter the same canonical project table.

Recommended change:

```python
def load_project_source(
    uploaded_file,
    utility_name: str,
    *,
    job_dir: Path,
    parser_hint: str | None = None,
) -> pd.DataFrame:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix == ".pdf":
        saved_path = save_uploaded_file(uploaded_file, job_dir)
        parsed = parse_uploaded_pdf(
            saved_path,
            utility_name,
            output_dir=job_dir,
            parser_hint=parser_hint,
        )
        return to_frontend_projects(parsed, utility_name)
    return load_uploaded_projects(...)
```

Do not make `data_loader.py` contain the entire PDF parser. Keep it as an input adapter and call the reusable backend service.

The setup page should accept:

```python
type=["pdf", "csv", "xlsx", "xlsm"]
```

It should also show the selected parser mode, for example:

- Georgia Power parser
- Dominion parser
- Generic parser / manual review

---

## 7. Connect location resolution to Overpass

The existing `gridlock_desc_locator.py` already implements the correct broad strategy:

1. Nominatim finds a general seed location for a named place.
2. Overpass searches nearby OSM power substations.
3. Candidate substations are scored by name, operator, voltage, and distance.
4. A HIGH/MEDIUM/LOW confidence result is written.
5. Results are cached so repeated runs do not repeat successful requests.

Reuse this logic through importable functions rather than constructing a new query in `3_Location_Confirm.py`.

### Required location service interface

```python
def resolve_project_locations(
    projects: pd.DataFrame,
    *,
    cache_path: Path,
    output_dir: Path,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (location_rows, project_rows_with_centers)."""
```

The service should return:

1. A detailed location table with one row per project endpoint/location.
2. A project-level table with center coordinates and confidence.

### Keep the public API safeguards

The current locator has important safeguards that must remain:

- Nominatim delay of about 1.1 seconds between requests.
- A descriptive `User-Agent`.
- Overpass fallback servers.
- Successful-response caching.
- No caching of transient failures.
- No network calls in automated tests.

The Streamlit UI should not directly call public APIs on every rerun or every widget change.

### Overpass query scope

The current locator searches nearby `power=substation` nodes, ways, and relations. If the workflow also needs transmission line geometry, add an explicit second query for relevant `power=line` or `power=minor_line` features, but do not assume line geometry is a single coordinate.

For a project described by two named transmission endpoints, resolve each endpoint separately and store both results against the same `(Utility, Project ID)`.

### Review behavior

Every LOW or MEDIUM result should appear in the Location Verification page with:

- Project ID
- Project name
- Target location name
- Seed display name
- Matched OSM name/operator/voltage
- Latitude/longitude
- Confidence
- Source
- Match score
- Reason text
- An editable replacement coordinate or selected candidate

Do not label a Nominatim town/county fallback as a confirmed utility asset.

---

## 8. Calculate center points correctly

The current backend summary function averages all located points. That is not exactly the desired rule for this project because LOW-confidence fallbacks can distort the center.

Implement a dedicated center policy.

### Recommended center algorithm

For each `(Utility, Project ID)`:

1. Select coordinates that are marked usable by the review policy.
2. If there are exactly two valid transmission endpoints, calculate their midpoint:

```python
center_latitude = (lat_1 + lat_2) / 2
center_longitude = (lon_1 + lon_2) / 2
```

3. If there is only one valid location, use it as the center.
4. If there are more than two locations:
   - Use the two explicitly identified endpoints when available.
   - Otherwise use a documented multi-site policy, such as the mean of HIGH/MEDIUM locations only.
5. If there are no valid coordinates, leave the center blank.
6. Store the method and confidence.

Example output fields:

```text
Center Latitude
Center Longitude
Center Method: endpoint_midpoint | single_location | reviewed_mean | unavailable
Center Confidence: HIGH | MEDIUM | LOW
```

### Important longitude edge case

For the current Georgia/South Carolina use case, the arithmetic midpoint of longitudes is acceptable. If the application later supports projects crossing the antimeridian, use a spherical midpoint implementation instead.

### Preserve auditability

The final row should retain both endpoint coordinates and the center calculation method. A reviewer should be able to reproduce the center without guessing which locations were used.

---

## 9. Build the overlap finder as a backend service

Move the pairwise comparison out of `4_Overlaps.py` into a reusable function:

```python
def find_overlaps(
    projects: pd.DataFrame,
    utility_a: str,
    utility_b: str,
    threshold_miles: float = 25.0,
) -> pd.DataFrame:
    """Return every Utility A/B pair whose centers are within the threshold."""
```

The service should:

1. Filter by exact utility name.
2. Require valid center coordinates.
3. Calculate haversine distance between center points.
4. Keep pairs where `distance_miles <= threshold_miles`.
5. Carry both project IDs, names, types, dates, voltages, confidence values, and center methods.
6. Calculate absolute in-service date gap.
7. Preserve the two endpoint coordinates for traceability.

Do not filter by `Match Status == Confirmed` unless the product decision explicitly requires that. The existing test data intentionally checks that coordinate-bearing excluded records can still participate in the current calculation. If the policy changes, make it a visible setting and document it.

Recommended overlap fields:

```text
Utility A
Project ID A
Project Name A
Utility B
Project ID B
Project Name B
Center Latitude A
Center Longitude A
Center Latitude B
Center Longitude B
Center Method A
Center Method B
Location Confidence A
Location Confidence B
Distance Miles
Start Date A
Start Date B
In-Service Date A
In-Service Date B
Date Gap Days
Voltage A
Voltage B
Project Type A
Project Type B
```

---

## 10. Use one ranking implementation

The repository has a root `ranking.py` and a separate `frontend/ranking.py`. Do not maintain two copies of the scoring rules.

Make the root `ranking.py` the authoritative implementation because it supports:

- Project enrichment by `(utility, project_id)`.
- Distance score.
- Timeline overlap score.
- Days-apart score.
- Voltage score.
- Project-type score.
- Explainable `ranking_reason`.

Then either:

- Import it directly from the frontend, or
- Move the shared implementation into a common package and make both entry points import it.

The final ranked result should include:

```text
Rank
Total Score
Distance Score
Timeline Overlap Score
Days Apart Score
Power Voltage Score
Project Type Score
Ranking Reason
```

The ranking code treats distance as the primary signal through its score and distance tie-break. Missing voltage/type information should score zero and be explained, not guessed.

---

## 11. Redesign the Streamlit page flow

### Page 1: Project Setup

Change the page to:

1. Ask for Utility A and Utility B names.
2. Accept one or more PDFs/CSVs/XLSX files for each utility.
3. Let the user select parser mode if needed.
4. Let the user choose the radius, defaulting to 25 miles.
5. Let the user click **Start Analysis**.
6. Save uploaded files to a job directory.
7. Start the parse job and show progress.

Do not set `st.session_state.projects` until parser output has passed basic schema validation.

### Page 2: Project Review

Show the normalized parser result before geocoding.

Required review columns:

- Utility
- Project ID
- Project Name
- Project Type
- Dates
- Voltage fields
- Location names
- Source pages
- Parser status/evidence status

Allow edits, but keep an audit note or an `Edited` flag when a user changes a parser value.

### Page 3: Location Verification

Replace the current “prepare query” placeholder with:

1. **Run location matching** button.
2. Progress and cache status.
3. Detailed endpoint candidate table.
4. Map of seed points, matched assets, and project centers.
5. Manual coordinate/candidate correction controls.
6. **Save location reviews** button.
7. **Continue to overlap calculation** button.

The page should call the location service, not create a one-off query string that is never executed.

### Page 4: Overlap Results

The page should only display the output of:

```text
projects_with_centers -> find_overlaps -> rank_overlaps
```

It should not recompute a different center policy locally.

Show:

- Number of projects per utility.
- Number of projects with usable centers.
- Number of LOW/MEDIUM centers.
- Number of qualifying pairs.
- Ranked table.
- Map with center points and 25-mile radius circles.
- Download button for ranked results.

### Page 5: Export

Export at least three files:

1. `projects_normalized.csv`
2. `project_locations_review.csv`
3. `ranked_overlap_results.csv`

Optionally export one ZIP containing all three plus:

- `manual_review.csv`
- `parser_evidence.json`
- `run_metadata.json`

`run_metadata.json` should contain the utility names, threshold, parser version, geocoder version, timestamp, input filenames, and job ID.

---

## 12. Suggested orchestration function

Create one orchestration function so the UI only needs to pass inputs and render outputs:

```python
def run_analysis(
    *,
    utility_a: str,
    utility_b: str,
    source_a: list[Path],
    source_b: list[Path],
    threshold_miles: float,
    job_dir: Path,
    progress_callback=None,
) -> AnalysisResult:
    """
    Parse, locate, calculate centers, find overlaps, rank, and export.
    """
```

The stages should be explicit:

```python
projects_a = parse_sources(source_a, utility_a, job_dir / "utility_a")
projects_b = parse_sources(source_b, utility_b, job_dir / "utility_b")

projects = validate_and_concat(projects_a, projects_b)
location_rows, projects = resolve_project_locations(projects, ...)
projects = calculate_project_centers(projects, location_rows)
overlaps = find_overlaps(projects, utility_a, utility_b, threshold_miles)
ranked = rank_overlaps(overlaps, projects=projects)
write_all_outputs(projects, location_rows, overlaps, ranked, job_dir)
return AnalysisResult(...)
```

Each stage should write a checkpoint file. If a later stage fails, the job can resume without parsing the PDF again.

---

## 13. Validation and error handling

Fail loudly when the input structure is invalid:

- PDF cannot be opened.
- Parser cannot find required sections.
- No project rows were extracted.
- Required project ID/name fields are absent.
- Duplicate `(Utility, Project ID)` keys exist unexpectedly.
- Dates or coordinates have invalid formats.

Warn, but preserve the row, when source data is incomplete:

- Missing start date.
- Missing voltage.
- Unknown project type.
- No geocoding result.
- LOW-confidence fallback.
- Conflicting dates in the source PDF.

Every warning should be attached to a project row or written to the job log. Do not silently repair source data.

### Minimum schema validation

```python
required = {"utility", "project_id", "project_name"}
missing = required - set(projects.columns)
if missing:
    raise ValueError(f"Parser output is missing columns: {sorted(missing)}")

key_counts = projects.groupby(["utility", "project_id"], dropna=False).size()
duplicates = key_counts[key_counts > 1]
if not duplicates.empty:
    raise ValueError("Duplicate utility/project ID keys found")
```

---

## 14. Testing plan

Tests must never call public Nominatim or Overpass servers.

### Unit tests

Add tests for:

1. PDF upload saving and file extension handling.
2. Parser adapter selection.
3. Canonical schema conversion.
4. Leading-zero project IDs.
5. Two-endpoint midpoint calculation.
6. Single-location center calculation.
7. Missing/LOW-confidence center behavior.
8. Haversine distance.
9. Threshold boundary: exactly 25 miles is included.
10. Date gap calculation.
11. Ranking output and tie-break behavior.
12. CSV export columns and ordering.

### Integration tests using existing synthetic data

Use:

```text
frontend/test_data/overlap_case/
frontend/test_data/utility_a_projects.csv
frontend/test_data/utility_b_projects.csv
```

The overlap case should produce these three qualifying pairs:

- Augusta North Expansion / Augusta West Tie
- Savannah River Corridor / Savannah East Station
- Midlands 230 kV Upgrade / Columbia South Substation

The Coastal North Project / Charleston Harbor Line pair should be outside the 25-mile threshold.

Mock the location resolver to return deterministic coordinates, then verify that the final ranked CSV matches expected project IDs, names, distances, and date gaps.

### Parser tests

Keep the existing parser tests and run the fast suite before every change:

```bash
.venv/Scripts/python -m pytest -m "not slow"
```

Run the full suite when parser code changes:

```bash
.venv/Scripts/python -m pytest
```

---

## 15. Recommended implementation order

Implement in this order to minimize risk:

### Phase 1: Backend contract

1. Define the canonical schema.
2. Add `to_frontend_projects()` and `validate_projects()`.
3. Add center calculation tests.
4. Add the overlap service tests.
5. Make the root ranking implementation callable from the frontend.

### Phase 2: Parser integration

1. Add PDF upload acceptance.
2. Save uploaded PDFs to job directories.
3. Add parser adapters for Georgia Power and Dominion.
4. Write parser outputs to the job directory.
5. Display parsed rows in Project Review.

### Phase 3: Location integration

1. Refactor locator functions into an importable service.
2. Preserve the cache and public API rate limits.
3. Add mocked location tests.
4. Call the service from Location Verification.
5. Add endpoint review and manual overrides.

### Phase 4: Center and overlap integration

1. Implement the endpoint midpoint policy.
2. Persist center method and confidence.
3. Replace frontend-local overlap calculations with the shared service.
4. Call the root ranking implementation.
5. Verify the synthetic overlap case.

### Phase 5: Export and resilience

1. Add checkpoint files and resumable jobs.
2. Add final project/location/ranked CSV exports.
3. Add a ZIP export with evidence and metadata.
4. Add progress reporting and friendly failure messages.
5. Run the full test suite and document known LOW-confidence rows.

---

## 16. Definition of done

The integration is complete when a user can perform this sequence without manually moving files:

1. Open the Streamlit app.
2. Enter two utility names.
3. Upload a large PDF for each utility.
4. Click **Start Analysis**.
5. Watch parser progress and see normalized project rows.
6. Review/edit parser output.
7. Run location matching.
8. Review matched Overpass candidates and confidence values.
9. Confirm or correct endpoints.
10. See project centers calculated using the documented midpoint policy.
11. See only cross-utility pairs inside the configured 25-mile radius.
12. See each pair ranked by the shared ranking implementation.
13. Download the final ranked CSV.
14. Reopen the job and reproduce every final number from the saved parser, location, center, and ranking files.

The most important principle is traceability: every final distance and ranking should be explainable from a project ID, source PDF page, selected coordinates, center-point method, threshold, and ranking components.

---

## 17. Immediate next task for implementation

The highest-value first code change is to create the shared pipeline contract and connect one known parser end-to-end before supporting arbitrary PDFs:

```text
Georgia Power PDF
  -> parsers.georgia_power
  -> canonical project DataFrame
  -> mocked location resolver
  -> endpoint midpoint
  -> overlap finder
  -> root ranking.py
  -> Streamlit Project Review / Overlap Results / Export
```

Once that path works with the existing synthetic overlap tests, add the real Overpass calls and then add the second utility/parser adapter. This avoids debugging PDF extraction, public APIs, Streamlit reruns, center calculations, and ranking simultaneously.
