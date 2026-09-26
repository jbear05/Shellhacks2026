# Parser handoff

Where the PDF-parsing work stands, so a new session can pick it up without
re-reading the PDFs. Last updated 2026-09-26.

## Status

- Branch `feat/gpc-pdf-parser` (PR into `main`) has a working, tested Georgia Power
  parser: `python -m parsers.georgia_power` writes
  `data/processed/georgia_power_projects.csv` with 208 projects.
- Next up: the Dominion (DESC) parser, then geocoding the Georgia Power locations and
  computing overlaps. See [Next steps](#next-steps).
- The PR was reviewed against the teammates' branches, including the new
  `origin/dominionScript`. The parser is ready to merge; what the other branches need
  to work with it is in [Integration review](#integration-review-2026-09-26).

## The challenge

Sperry Tech "Gridlock" (ShellHacks 2026): compare planned transmission projects of
Dominion Energy South Carolina (DESC) and Georgia Power (GPC). Flag pairs within
25 miles (primary signal) and with overlapping build windows (secondary). Deliver an
interactive map and a ranked list of coordination opportunities; bonus for a
cost/impact estimate on one of them.

Files in `Sperry-Tech-Challenge/`:

- `ShellHacks_Challenge_Gridlock.docx`: the brief.
- `Finding_Real_Locations_Guide.docx`: suggested method (OSM Overpass/Nominatim for
  coordinates, verify against the PDF, haversine between project centers).
- `Projects_Overlaps.xlsx`: target schema. `projects` sheet has name_a/lat_a/lon_a,
  name_b/lat_b/lon_b, a center (midpoint, or the one located point) and
  in_service_date. `overlaps` sheet has distance_mi and time_gap (days between
  in-service dates).
- `Project Listings/`: the two source PDFs.

## Branches

| Branch | Who | What |
|---|---|---|
| `main` | | Challenge files only |
| `feat/gpc-pdf-parser` | us | Parser package, tests, generated CSV, README, this file |
| `origin/Geolocator` | teammate | `gridlock_desc_locator.py` (Nominatim + Overpass locator for the 44 DESC projects, which are typed into a `PROJECTS` list by hand, or for a parser CSV via `--projects-csv`), `locator.py`, `projects.csv`, `desc_project_locations.csv`, geocode cache. Merged into `main`; usage in the README |
| `origin/NA` | teammate | UI pages `1_Project_Setup.py` to `5_Export.py` |
| `origin/dominionScript` | teammate | `dominionScript.py`: a first DESC parser (PyPDF2) that prints each project's ID, title and in-service date |

## What's built

| Path | Purpose |
|---|---|
| `parsers/common.py` | `normalize_text`, `parse_us_date`, `extract_voltages` (volts), `extract_miles`; meant for the DESC parser too |
| `parsers/georgia_power.py` | The parser and CLI (`--pdf`, `--out`, `--sponsors`, `-v`) |
| `tests/test_common.py`, `tests/test_georgia_power.py` | Unit tests on text samples copied from pypdf's output |
| `tests/test_georgia_power_pdf.py` | Integration tests on the real PDF, marked `slow` |
| `data/processed/georgia_power_projects.csv` | Committed output so teammates don't need Python |
| `README.md` | Setup, usage, column notes |

Commits on the branch: tooling, then shared helpers, then the parser, then the
CSV, then the README, then this file.

## How to run

From the repo root (Windows):

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m parsers.georgia_power
.venv/Scripts/python -m parsers.georgia_power --sponsors GPC SAV
.venv/Scripts/python -m pytest
.venv/Scripts/python -m pytest -m "not slow"
```

The parser must be run with `-m` from the repo root; `python parsers/georgia_power.py`
fails to import. A full run takes about 10 s; all 74 tests take 15-20 s.

## Georgia Power PDF: what we learned

`Project Listings/Georgia Power/2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf`, 668 pages,
real text (no OCR needed).

- **Finding the plan:** use the bookmarks. "2 - 2024 GA ITS Ten Year Plan" covers PDF
  pages 171-474. PDF page = the plan's own page number + 170.
- **Table 2 (project list), PDF 177-190.** Columns: Zone, Year, TEAMS #, Project Name,
  Need Date, Sponsor, then costs, which are all `REDACTED`.
  - Names wrap over 2-3 lines, so rows are matched from the zone/year/TEAMS start to
    the date/sponsor/REDACTED end, not line by line.
  - The table ends at a `Total REDACTED ...` row. Tables 3 (Cancelled) and 4
    (Completed) follow on PDF 191-192 and must be excluded.
- **Section IV detail pages (PDF 214-425):** one per project, found by the
  `Teams # NNNNN` header, with Need Date and Start Date on the next line.
  - pypdf prints all form labels first and their values afterwards, so values are
    read by position after removing the fixed form text. The remainder is always:
    description, `REDACTED` (supporting statement), change vs previous plan, change
    vs previous IRP.
  - East Walton (TEAMS 09662) spills onto a second page. Cutting the text into one
    chunk per project first is what stops it swallowing the next project.
- **Boilerplate:** every page repeats a CEII banner, a "Page N of 304" footer,
  "PUBLIC DISCLOSURE" and the table header. The parser strips all of them. This file
  is the redacted public version supplied by the organizers.
- **Sponsors:** GPC 122, GTC 54, SAV 16, MEAG 14, DU 2 (208 total). Georgia Power
  itself = GPC + SAV (Savannah area); the organizers' example sheet counts SAV
  projects as Georgia Power. All sponsors are kept; filter downstream.
- **Source inconsistencies:** TEAMS 19523, 20684 and 17900 have different need dates
  in Table 2 and on their detail pages. The parser uses Table 2 and logs a warning.
  TEAMS 20248 (Bay Creek - Conyers) starts 2031-06-01 but is due 2029-12-31 in both
  places; no warning is logged for it yet.
- **Costs:** every Georgia Power cost is redacted.

## Output columns worth knowing

The README has the full list. Things to keep in mind:

- **IDs and dates:** `project_id` is the TEAMS number. `in_service_date` is the
  Table 2 need date. `start_date` comes from the detail page, so a project's build
  window is start to in-service.
- **Guessed from the title:** `location_1..3`, `project_type` and `voltage_1..2`.
  They match the Geolocator's `projects.csv` conventions (voltages in volts). Known
  weak rows:
  - No location at all (`UNKNOWN`): 20466 "SMART VALVE INSTALLATION" and 20223
    "CC - PROJECT PAYTON BAINBRIDGE".
  - Customer-project names that aren't substations: QCELLS, SK/HYUNDAI, NORTH GEORGIA,
    HYUNDAI MOTORS SAVANNAH.
- **`owner_tags`:** owners named in the title. `USA` (federal), `APC` (Alabama Power)
  and `FPL` endpoints won't have Georgia Power as their OpenStreetMap operator.
- **Mileage:** `line_miles` is set only when a description gives exactly one mileage.
  11 projects give several, and `miles_mentioned` lists them all.

## Decisions made

- **pypdf + regex, not an LLM, for the structured fields.** Results are verifiable
  (row counts reconcile) and the same every run.
- **An LLM only for the fuzzy step,** if at all: title to endpoint names, location
  hints from descriptions. Cache the results to JSON, check values against the source
  text, and never call it at app runtime.
- **Parse offline to CSV;** the app reads the CSV.
- **`project_id` is the source ID** (TEAMS number, or the DESC "Project ID"), matching
  the teammate's convention.
- **Fail loudly on structure changes:** `ParseError`, exit code 1, no CSV written.
  Problems in the source data only produce warnings.
- **Dependencies are pinned** (`pypdf==6.19.0`), because the regexes depend on
  pypdf's exact output.

## Next steps

1. **DESC parser** (`parsers/dominion.py`), starting from the teammate's
   `dominionScript.py` rather than writing a second one, plus a `normalize_project_id`
   helper; see [DESC parser notes](#desc-parser-notes) and
   [Project IDs](#project-ids). Check with the teammate first.
2. **Manual overrides:** a CSV keyed by project ID, merged over the heuristic columns,
   to fix the UNKNOWN and customer-project rows. This was a review finding we chose
   not to fix yet.
3. **Geocode Georgia Power.** The locator reads the parser CSV now (see the README's
   Geolocator section). Run it, then go through `georgia_power_manual_review.csv`.
   Known wrong lookups, for the overrides file:
   - `EVANS PRIMARY` finds Evans County instead of the town of Evans (Columbia County).
   - `MCINTOSH` finds McIntosh County instead of Plant McIntosh (Effingham County).
   - A candidate with the wrong name can still score MEDIUM on operator, voltage and
     distance alone.
4. **Overlaps.**
   - Distance: haversine between project centers (midpoint of the two endpoints, or
     the single located point). Under 25 mi makes an overlap row.
   - `time_gap`: days between in-service dates.
   - Build windows: Georgia Power = [start_date, in_service_date]. DESC = [first year
     with nonzero spend, in-service date].
   - Don't assume start <= in-service (TEAMS 20248), and add a warning for it in
     `find_inconsistencies`.
   - Carry each project's location confidence into the overlap rows, so reviewers can
     see which centers are only a town or county.
5. **Bonus cost estimate:** Georgia Power costs are redacted. Work out $/mile from DESC
   projects whose descriptions give miles and apply it to Georgia Power's
   `line_miles`.
6. **Possible performance tweak** (the other review finding we skipped): stop text
   extraction after the last detail page. PDF 426-474 are extracted but unused, which
   costs about 1.5 s.

## Integration review (2026-09-26)

A review of this PR against the teammates' branches. Check with them before editing
their branches. The Geolocator findings have since been fixed on that branch; see
below.

### Geolocator (`origin/Geolocator`)

Fixed on the branch before it was merged into `main`:

- **State per project.** Each location is searched in its project's `state`, except
  those in `LOCATION_STATE_OVERRIDES` (Purrysburg, SC, for GA 20277). Retrying in the
  other state was rejected: DESC's "North Bridge Terrace" searched in Georgia finds a
  shop in Augusta. Thurmond Dam needs no override, because its top result in a Georgia
  search is the dam on the SC side.
- **Operator names per utility.** `OPERATOR_ALIASES` is keyed by `utility`. OSM tags
  Georgia substations "Georgia Power", even around GTC and MEAG projects, so all four
  Georgia owners accept that name.
- **Strings.** The CSV loader uses the csv module, so voltages stay `"115000"` and IDs
  like `09662` keep their leading zero. With pandas, pass
  `dtype=str, keep_default_na=False`.
- **Search name vs match name.** Only `PRIMARY` is dropped from the Nominatim query:
  "Evans Primary" finds nothing, while "Aultman Road", "Thurmond Dam" and
  "Plant Yates" search fine as they are.
- **Output paths.** `--output-prefix`.
- **Overpass.** Results are cached, and failed requests are marked and retried on the
  next run instead of looking like "no substation nearby".

Still open:

- **Scale.** Georgia has 353 location slots (215 distinct names); DESC 101. Probably
  only Georgia projects around Savannah and Augusta can be within 25 mi of a DESC
  project, so the manual review could be limited to those.
- **Project centers.** `build_project_summaries` averages every located point,
  including the LOW-confidence fallbacks where only the town or county was found (for
  example "Jasper" becomes the middle of Jasper County). Keep `overall_confidence`
  with the center.

### dominionScript (`origin/dominionScript`)

Checked by running a copy on the real PDF:

- **It doesn't run as committed.** It imports `PyPDF2` (not installed; we pin
  `pypdf`) and opens the PDF by bare filename from the working directory. With
  `import pypdf as PyPDF2` and the real path it reads all 44 projects with no
  `Unknown` fields, so its regexes work with pypdf 6.19.0.
- **Three fields only.** ID, title and in-service date, as raw strings, printed to the
  console. It runs on import and prints page 1's raw text for debugging. Still needed:
  the 7 cost amounts, the description (for miles) and a CSV output.
- **One date can't be read:** 6859 Dawson (page 34) has two phase dates, which
  `parse_us_date` rejects.
- **Plan:** move its regexes into `parsers/dominion.py` (credited to the teammate),
  built on `parsers.common`, instead of keeping two DESC parsers.

### Project IDs

The DESC PDF writes `06367 A - C, H` and `06367 D - G`; the Geolocator's list has
`06367 A-C, H` and `06367 D-G`. The other 42 IDs match exactly. A plain join on
`project_id` drops these two (Riverport Tap and Jasper - Okatie #2), which are next to
Savannah. Add `normalize_project_id` to `parsers/common.py` (remove spaces around `-`
and `,`) and apply it on both sides.

- Titles differ in spacing too (`Yemassee- Ritter` vs `Yemassee-Ritter`). Join on ID,
  never on name.
- Georgia TEAMS numbers are all 5 digits and don't collide with DESC IDs today, but
  key shared tables on (`utility`, `project_id`).

### UI (`origin/NA`)

- `4_Overlaps.py` expects columns `Project Name`, `Utility`, `Project Type`,
  `In-Service Date`, `Latitude` and `Longitude`; `2_Project_Review.py` adds
  `County / Region` and `Match Status`.
- It keeps rows whose `Utility` exactly equals the name typed on the setup page. Use
  `Georgia Power` (GPC + SAV; leaves out GTC, MEAG and DU) and
  `Dominion Energy South Carolina`.
- The review page builds sample rows for now; it needs to load the merged project and
  location table.

### Shared columns

Both parsers should emit `utility`, `project_id`, `state`, `project_name`,
`project_type`, `location_1..3`, `voltage_1..2`, `in_service_date` and `start_date`,
so the overlap code doesn't branch on utility. For DESC, `start_date` comes from the
first year with nonzero spend (a nonzero `Previous` amount means before 2024). DESC
locations come from the Geolocator's hand-typed list, joined on the normalized ID: it
includes endpoints taken from the descriptions (Blue Circle, Owens Corning) that a
title heuristic would miss.

### Dependencies

`requests` and `pandas` are in `requirements.txt` since the Geolocator merge. The UI
branch still needs `streamlit`. `origin/dominionScript` already uses `pypdf`.

### Likely overlap candidates

Not geocoded yet; picked from names and dates only.

| Georgia Power | DESC | Why |
|---|---|---|
| 20277 McIntosh - Purrysburg 230 kV, 2024-01-01 to 2026-06-01 | 06367 A-C, H Riverport Tap and 06367 D-G Jasper - Okatie #2, both due 12/31/25 | Jasper County, next to Savannah; build windows overlap |
| 20793/20794 Evans Primary - Thurmond Dam #5/#6, 2029-2030 to 2033-06-01 | 6810 A Hooks - Thurmond Tie, due 12/31/2024 | Same dam endpoint; build windows don't overlap |

Also worth checking: the Augusta-area DESC projects (Stevens Creek - Hooks,
Urquhart - Toolebeck, Urquhart - Aiken PSA) against Georgia's Evans and Thomson
projects.

## DESC parser notes

These come from a prototype that was not committed. Running the teammate's
`dominionScript.py` confirmed the title, ID and date findings.

`Project Listings/Dominion Energy/2024-2028-2million-and-above-project-descriptions.pdf`:
44 pages, one project per page, exported from Word, real text.

- **Title:** between `5 Year Budget` and `Project ID`.
- **Labels:** each on its own line: `Project ID`, `Project Description`,
  `Project Need`, `Project Status`, `Planned In-Service Date`,
  `Estimated Project Cost`. Split the page on them.
- **Cost table:** the header is `Previous 2024 2025 2026 2027 2028 Total*`, but the
  asterisk is missing on pages 14, 15 and 25. The cells wrap unpredictably, so take
  the `$` amounts in order: there are always exactly 7 (prior, 2024-2028, total).
  The years with nonzero spend give the build window.
- **Dates:** a mix of `12/31/23` and `12/31/2024`. Page 34 has
  `10/1/2025 (phase 1) and 10/1/2026 (phase 2)`, so find every date in the field.
- **Dashes:** names and descriptions mix en-dashes and hyphens; run `normalize_text`.
- **Mileage:** some pages give miles (page 14 "9.5 miles", page 20 "Approx 18 Miles"),
  which the $/mile estimate needs.
- **Reuse the teammate's work:** `gridlock_desc_locator.py` on `origin/Geolocator`
  already lists locations for all 44 projects by hand. Compare with it rather than
  re-deriving them. Its IDs are the DESC Project IDs (e.g. `6807 B`), but two are
  spaced differently from the PDF; see [Project IDs](#project-ids).
- **Validate:** 44 rows, 7 cost amounts per page, every date parsed, and every ID
  found in the Geolocator's list after normalizing.

## Environment notes

- **Shell:** Windows, with Git Bash and PowerShell. Use `.venv/Scripts/python`.
- **Line endings:** `core.autocrlf=true`, so the LF/CRLF warnings on commit are
  harmless.
- **Command hook:** a safety hook blocks `rm -rf` and shell redirects (`>`) to paths
  held in variables. Write to literal paths or use the editor.
- **Testing one commit:** long temp paths plus the long PDF filenames exceed Windows'
  path-length limit, so `git worktree add` there fails. Extract just the code instead:
  `git archive <commit> parsers tests pyproject.toml | tar -x -C <dir>`.
