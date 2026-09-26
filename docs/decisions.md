# Decisions

Why things are the way they are. Add new decisions at the end with the date. If a
decision is reversed, say so under the old entry instead of deleting it.

## Parsing

- **pypdf and regexes, not an LLM, for the structured fields** (2026-09-26). The
  results can be verified (row counts reconcile) and are the same on every run.
- **An LLM only for fuzzy steps, if at all** (2026-09-26): title to endpoint names,
  location hints from descriptions. Cache the results to a file, check each value
  against the source text, and never call it while the app runs.
- **Parse offline to CSV, and commit the CSVs** (2026-09-26). The app reads the CSV,
  and teammates don't need Python or the PDFs to use the data.
- **Fail loudly on structure changes** (2026-09-26): `ParseError`, exit code 1, no CSV
  written. Problems in the source data only produce warnings.
- **Pin `pypdf==6.19.0`** (2026-09-26), because the regexes depend on its exact text
  output.
- **Keep every Georgia sponsor and filter downstream** (2026-09-26). GPC, SAV, GTC,
  MEAG and DU are all in the CSV. The organizers' example counts SAV as Georgia Power.
- **Georgia's `in_service_date` is the Table 2 need date** (2026-09-26). The detail
  page disagrees for 3 projects; its value is kept in `detail_need_date`.
- **The DESC parser stays in the teammate's `dominionScript.py`** (2026-09-26),
  reworked in place rather than moved into `parsers/dominion.py`, so the teammate's
  work and history stay where they left it.
- **DESC `start_date` is January 1 of the first year with spending, or blank**
  (2026-09-26). The PDF has no start date. Spending under "Previous" means work began
  before 2024 on an unknown date, and we don't make one up.
- **DESC locations come from the Geolocator's hand-typed list, not the parser**
  (2026-09-26). The list already has all 44 projects, including endpoints that only
  the descriptions name.

## IDs and joins

- **`project_id` is the source's own ID** (2026-09-26): the TEAMS number, or the DESC
  "Project ID". Shared tables are keyed on (`utility`, `project_id`).
- **DESC IDs are spelled as in the Geolocator's list** (2026-09-26). The parser
  removes the spaces around `-` (`06367 A - C, H` becomes `06367 A-C, H`) but not
  around `,`, which the list keeps in `1060A, I, L`. Neither side needs a normalizing
  step to join.

## Geolocator

- **Search each location in its project's state, with explicit overrides**
  (2026-09-26). Retrying a missing name in the other state was rejected: "North Bridge
  Terrace" searched in Georgia finds a shop in Augusta.
- **Only `PRIMARY` is dropped from Nominatim queries** (2026-09-26). "Evans Primary"
  finds nothing, while "Aultman Road", "Thurmond Dam" and "Plant Yates" work as they
  are.
- **Operator names per utility** (2026-09-26). OpenStreetMap tags Georgia substations
  "Georgia Power" even around GTC and MEAG projects, so all four Georgia owners accept
  it.
- **Failed Overpass requests are retried, not cached** (2026-09-26), so a failure
  doesn't look like "no substation nearby".

## Process

- **Merge teammates' pull requests with a merge commit** (2026-09-26), so their
  commits keep their author.
- **Agent instructions live in `AGENTS.md`, and project knowledge in `docs/`**
  (2026-09-26). `AGENTS.md` is read by most coding agents, and `CLAUDE.md` imports it
  for Claude Code. The single `parser-handoff.md` was split into topic docs, so a
  session loads only what its task needs, and `tests/test_docs.py` keeps links and
  column lists in step with the code.
