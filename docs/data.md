# Data dictionary

Every column of every CSV the pipeline writes, and how the files join.
`tests/test_docs.py` checks that each table below lists its file's columns, in order.

## Reading the CSVs

- **IDs are text.** Three TEAMS numbers (`09662`, `08458`, `09661`) and 14 DESC IDs start
  with 0, and DESC IDs contain spaces and commas (`1060A, I, L`). With pandas, use
  `pd.read_csv(path, dtype=str, keep_default_na=False)`. The csv module keeps
  everything as strings already.
- **Encoding:** the parser CSVs are UTF-8. The Geolocator's outputs are UTF-8 with a
  BOM (`utf-8-sig`), so read them with `encoding="utf-8-sig"` or the first column is
  named `﻿project_number`.
- **Units:** dates are ISO `YYYY-MM-DD`, voltages are in volts, distances in miles,
  and costs in whole dollars.
- **Lists in one cell** are separated by `; ` (`miles_mentioned`, `owner_tags`), or by `;`
  in the Geolocator's `expected_voltages`.

## Keys

- A project is identified by (`utility`, `project_id`). IDs don't collide between the
  utilities today, but key shared tables on both columns anyway.
- `project_id` is the source's own ID: the TEAMS number for Georgia, and the Project ID
  for DESC, spelled as in the Geolocator's list (see
  [sources/dominion-pdf.md](sources/dominion-pdf.md#project-ids)).
- Never join on names. Spacing and case differ between the PDF and the Geolocator's
  list (`Yemassee- Ritter` and `Yemassee-Ritter`).
- The Geolocator's `project_number` is only the row's position in that run's input.
  Don't join on it.

## Columns both parsers share

`project_id`, `utility`, `sponsor`, `state`, `project_name`, `in_service_date`,
`start_date`, `line_miles`, `miles_mentioned` and `description` mean the same thing in
both parser CSVs, so the overlap code doesn't need to branch on utility. A project's
build window runs from `start_date` to `in_service_date`.

The DESC CSV has no `project_type`, `location_*` or `voltage_*` columns. For DESC those
come from the Geolocator's hand-typed `PROJECTS` list, joined on (`utility`,
`project_id`); see [pipeline.md](pipeline.md#1-parse).

## `data/processed/georgia_power_projects.csv`

Written by `python -m parsers.georgia_power`: 208 rows, one per project in the
Ten-Year Plan's Table 2, joined to its detail page on TEAMS number. The columns
marked *heuristic* are guessed from the title; check them before relying on them.

| Column | Meaning |
|---|---|
| `project_id` | TEAMS number, 5 digits, text |
| `utility` | The sponsor spelled out: `Georgia Power` (GPC and SAV), `Georgia Transmission Corporation`, `MEAG Power`, `Dalton Utilities` |
| `sponsor` | `GPC` 122, `GTC` 54, `SAV` 16, `MEAG` 14, `DU` 2. SAV is Georgia Power's Savannah area |
| `state` | Always `Georgia`. GA 20277 McIntosh - Purrysburg ends in South Carolina |
| `project_name` | Table 2 title as printed (upper case), whitespace collapsed |
| `project_type` | *Heuristic.* `LINE` 138, `SUBSTATION` 62, `MULTI_SITE` 3, `MULTI_LINE` 2, `UNKNOWN` 2, `BOTH` 1 (a loop-in or fold-in) |
| `location_1` | *Heuristic.* First place name in the title, upper case |
| `location_2` | *Heuristic.* Second place name, or blank |
| `location_3` | *Heuristic.* Third place name, or blank |
| `other_locations` | *Heuristic.* Fourth and later names, `; `-separated. Empty in every current row |
| `voltage_1` | Highest voltage in the title, in volts; taken from the description if the title has none |
| `voltage_2` | Second-highest voltage, or blank |
| `in_service_date` | Table 2 need date |
| `start_date` | Start date from the detail page. Can be later than `in_service_date` (TEAMS 20248) |
| `plan_year` | Table 2 "Year" |
| `zone` | Table 2 "Zone", a 3-digit code |
| `owner_tags` | Owners named in brackets in the title: `USA` (federal) 3, `APC` (Alabama Power) 3, `SAV` 2, `GPC` 1, `FPL` 1 |
| `line_miles` | The mileage when the description gives exactly one (117 rows) |
| `miles_mentioned` | Every mileage in the description, in order; 11 rows give more than one |
| `description` | Scope text from the detail page |
| `change_from_previous_plan` | Detail page field, for example `New Project` |
| `change_from_previous_irp` | Detail page field, for example `Project delayed from 2024 to 2025` |
| `detail_need_date` | Need date on the detail page. It differs from `in_service_date` for TEAMS 19523, 20684 and 17900 |
| `table_page` | PDF page (1-based) of the Table 2 row |
| `detail_page` | PDF page (1-based) of the detail page |

Weak rows:

- No location at all (`UNKNOWN`): 20466 "SMART VALVE INSTALLATION" and 20223
  "CC - PROJECT PAYTON BAINBRIDGE".
- Customer-project names that aren't places: QCELLS, SK/HYUNDAI, NORTH GEORGIA,
  HYUNDAI MOTORS SAVANNAH.
- Endpoints tagged `USA`, `APC` or `FPL` won't have Georgia Power as their
  OpenStreetMap operator.

## `data/processed/dominion_projects.csv`

Written by `python dominionScript.py`: 44 rows, one per page of the DESC PDF.

| Column | Meaning |
|---|---|
| `project_id` | DESC Project ID with the spaces around `-` removed, for example `6807 B`, `06367 A-C, H`, `1060A, I, L` |
| `utility` | Always `Dominion Energy South Carolina` |
| `sponsor` | Always `DESC` |
| `state` | Always `South Carolina` |
| `project_name` | Title as printed, with typographic dashes changed to hyphens |
| `in_service_date` | The last date in "Planned In-Service Date". 6859 Dawson gives one per phase |
| `start_date` | January 1 of the first year from 2024 to 2028 with spending. Blank for the 29 projects with `cost_previous` above 0: they started before 2024 on an unknown date |
| `line_miles` | The mileage when the title and description together give exactly one (19 rows) |
| `miles_mentioned` | Every mileage in the title and description |
| `description` | "Project Description" text |
| `cost_previous` | Spent before 2024 |
| `cost_2024` | Budget for 2024 |
| `cost_2025` | Budget for 2025 |
| `cost_2026` | Budget for 2026 |
| `cost_2027` | Budget for 2027 |
| `cost_2028` | Budget for 2028 |
| `cost_total` | "Total" as printed. It isn't the sum of the other amounts for 0139 M,N, 06367 A-C, H and 06810 F (see [sources/dominion-pdf.md](sources/dominion-pdf.md#cost-table)) |

## `data/processed/ai/<prefix>_projects.csv`

Written by `python -m parsers.ai_parser`: one row per project the model read from the
PDF, whatever its layout. How the values are read and checked is in
[ai-parser.md](ai-parser.md). A value that failed a check is blank, and its row is
`NEEDS_REVIEW`. Its columns are the Georgia parser CSV's, without the Georgia-only ones
(`plan_year`, `zone` and the rest), plus `pages` and `status`, so the file can go to
the Geolocator's `--projects-csv`.

| Column | Meaning |
|---|---|
| `project_id` | The ID as printed, with the spaces around `-` removed (the DESC rule) |
| `utility` | The owner, from the sponsor. For Georgia Power's plan, the sponsor code's utility, as in `georgia_power_projects.csv`; blank if no sponsor was read. Otherwise `--utility`, unless the printed sponsor names another. See [ai-parser.md](ai-parser.md#how-it-works) |
| `sponsor` | As printed for the project, or `--sponsor` if the PDF prints none |
| `state` | `--state`, on every row |
| `project_name` | The title as printed, whitespace collapsed, dashes as hyphens |
| `project_type` | Always blank. The Geolocator only passes it through |
| `location_1` | First place name the model found in the title and description, as printed |
| `location_2` | Second place name, or blank |
| `location_3` | Third place name, or blank |
| `other_locations` | Fourth and later names, `; `-separated |
| `voltage_1` | Highest kV figure in the title (or the description if the title has none), in volts |
| `voltage_2` | Second-highest, or blank |
| `in_service_date` | In-service or need date. For a phased project, the last phase's. When two places disagree, the earlier page's |
| `start_date` | Start date, only when the PDF prints one. Blank for DESC |
| `line_miles` | The mileage when the title and description give exactly one |
| `miles_mentioned` | Every mileage in the title and description |
| `description` | The scope text, joined across pages |
| `pages` | PDF pages (1-based) the row's values came from, `; `-separated |
| `status` | `VERIFIED`: every value passed its checks. `NEEDS_REVIEW`: see the review file |

`<prefix>_evidence.json`, next to it, holds every value with the quote and page it came
from, the model's label for each page, and the run's settings.

## `data/processed/ai/<prefix>_review.csv`

Written by `python -m parsers.ai_parser`: one row per problem.

| Column | Meaning |
|---|---|
| `project_id` | The project, or blank for a problem with a page |
| `field` | The column the problem is in, `locations`, `project_id` or `page` |
| `value` | The value that was rejected or not kept, if any |
| `quote` | The text the model said it copied |
| `page` | The page it cited, or the page the problem is on |
| `reason` | What failed, for example "not on page 14, but on page 34" |

## `<prefix>_project_locations.csv`

Written to `data/processed/` by `gridlock_desc_locator.py`: one row per location name
of each project. The prefix is `desc` by default, or the `--output-prefix` value. How the values are found
is in [geolocator.md](geolocator.md).

`<prefix>_manual_review.csv` has the same columns, with only the rows that aren't
HIGH.

| Column | Meaning |
|---|---|
| `project_number` | Position of the project in this run's input, from 1. Don't join on it |
| `project_id` | From the input |
| `utility` | From the input |
| `state` | From the input: the project's state, even when the location was searched in another state |
| `project_name` | From the input |
| `project_type` | From the input |
| `location_role` | `location_N`: the position of the name in the project's list. For a parser CSV, it's the parser column the name came from (`location_1` to `location_3`). The built-in DESC list reaches `location_4` for 6807 B and 6859 |
| `target_location` | The location name |
| `expected_voltages` | The project's voltages in volts, `;`-separated |
| `seed_latitude` | Nominatim's first result for the name; blank if none |
| `seed_longitude` | As above |
| `seed_display_name` | Nominatim's full name for that result |
| `matched_name` | Best OpenStreetMap substation's `name` tag, or `Unnamed` |
| `matched_operator` | Its `operator` tag, or `Unknown` |
| `matched_voltage` | Its `voltage` tag, or `Unknown` |
| `latitude` | The matched substation. If none matched, the seed point (a LOW fallback). Blank if Nominatim found nothing |
| `longitude` | As above |
| `osm_id` | The matched OpenStreetMap element |
| `osm_type` | `node`, `way` or `relation` |
| `distance_from_seed_miles` | From the seed point to the matched substation |
| `match_score` | 0 to 12; see [geolocator.md](geolocator.md#scoring) |
| `confidence` | `HIGH`, `MEDIUM` or `LOW` |
| `source` | `OpenStreetMap / Overpass`, `Nominatim general-location fallback` or `No match` |
| `reasons` | The scoring reasons, `; `-separated, or why nothing was found. "... re-run to retry" means a request failed |

## `<prefix>_projects_summary.csv`

Written to `data/processed/` by `gridlock_desc_locator.py`: one row per input project,
including projects with no location names.

| Column | Meaning |
|---|---|
| `project_number` | As in the locations file |
| `project_id` | From the input |
| `utility` | From the input |
| `state` | From the input |
| `project_name` | From the input |
| `project_type` | From the input |
| `expected_voltages` | As in the locations file |
| `total_locations` | Number of location names |
| `located_locations` | Number of them with coordinates |
| `overall_confidence` | The lowest confidence among its locations; `LOW` if it has none |
| `centroid_latitude` | Mean of every located point, including LOW fallbacks; blank if none |
| `centroid_longitude` | As above |
| `location_coordinates` | `name: lat,lon (CONFIDENCE)` for each location, joined with ` \| ` |

## `data/test/*_test_projects.csv`

Made-up projects for testing the stages after the parsers without the PDFs. Nothing in
them comes from a source PDF, so they stay out of `data/processed/`. A teammate added
them in https://github.com/jbear05/Shellhacks2026/pull/8. The originals are in
`data/test/raw/`, and `python clean_test_csvs.py` writes the cleaned copies:

- `desc_test_projects.csv`, from `raw/code.csv`: 65 projects, IDs 30006-30070, with the
  real DESC `utility` (`Dominion Energy South Carolina`), so never load it together with
  `dominion_projects.csv`. No coordinates: it has to go through the Geolocator's
  `--projects-csv`, with `--output-prefix desc_test`. The default prefix, `desc`,
  would overwrite the real DESC outputs in `data/processed/`.
- `duke_test_projects.csv`, from `raw/dukeEnergyCarolinas.csv`: 100 `Duke Energy
  Carolinas` projects, IDs 40001-40100, 49 in North Carolina and 51 in South Carolina,
  with coordinates.

The raw rows have more values than their headers have columns: a stray blank after
`other_locations`, another after `owner_tags`, and in the Duke file's 21
single-location rows a third after `location_2_lon`. pandas reads `raw/code.csv` with
every column shifted and fails on the Duke file. The script drops those blanks, stops
with an error if a value lands in a column of the wrong type, and writes voltages as
whole volts (`230000`, not `230000.0`). Every other value is copied unchanged.

Both files start with the 25 columns of `georgia_power_projects.csv`, in the same
order. The differences: `project_name` starts with `DESC: ` or `DEC: `, `zone` is a
region name such as `Lowcountry` rather than a 3-digit code, `start_date` is always
set, the page columns point to no real PDF, and `location_3`, `other_locations` and
`owner_tags` are empty. `project_type` is only `LINE` or `SUBSTATION`. The Duke file
adds:

| Column | Meaning |
|---|---|
| `location_1_lat` | Latitude of `location_1`, as given. Not checked against a geocoder |
| `location_1_lon` | As above |
| `location_2_lat` | Latitude of `location_2`; blank for the 21 single-location projects |
| `location_2_lon` | As above |
| `center_lat` | Midpoint of the two locations, or `location_1` for a single-location project |
| `center_lon` | As above |
| `confidence_score` | `High` 78, `Medium` 22, as given. The Geolocator writes upper case |

Weak rows. The script logs the first three on every run; the rest were found by hand
on 2026-09-26:

- 17 Duke lines have endpoints more than twice their `line_miles` apart, for example
  40053 Camden - Wilmington: 155.6 miles apart for a 17.4-mile line. Their centers
  aren't near where a real line would be.
- 6 projects are typed `LINE` though the name is station work (30038, 30044, 30060,
  30070, 40058, 40066), and 5 Duke `SUBSTATION` projects have a second location or line
  miles (40048, 40072, 40084, 40085, 40100).
- Duke `WILLIAMSTON` (40017) is at 32.74, -80.82, in the Lowcountry. The town of that
  name is in Anderson County, in the Upstate.
- Some Duke projects in North Carolina are labeled South Carolina, for example 40077
  Shelby - Cherryville.
