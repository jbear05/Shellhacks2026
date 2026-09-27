# Decisions

Why things are the way they are. Add new decisions at the end with the date. If a
decision is reversed, say so under the old entry instead of deleting it.

## Parsing

- **pypdf and regexes, not an LLM, for the structured fields** (2026-09-26). The
  results can be verified (row counts reconcile) and are the same on every run.
  Widened later the same day: an AI parser reads PDFs that have no parser of their own,
  and these parsers are the reference it's scored against. See [AI parser](#ai-parser).
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
- **Failed Nominatim and Overpass requests are retried, not cached** (2026-09-26), so
  a failure doesn't look like "not found" or "no substation nearby".
- **Substations are downloaded in 1° tiles, not one `around:` query per location**
  (2026-09-26). The per-location queries took about 36 s each and 4 of the first 10
  timed out, which put a full run at hours. Tiles are cached and shared by nearby
  locations, and they send far fewer requests. Distance is measured to a substation's
  center rather than its nearest edge; on 5 seeds the candidates were the same apart
  from one unnamed substation just past 25 km. A tile that fails is split into quarters
  because the dense Atlanta tiles timed out on both servers.
- **Every Georgia sponsor is geocoded, not just GPC and SAV** (2026-09-26). It cost a
  few minutes more, and it keeps the summary one row per project of
  `georgia_power_projects.csv`. Which owners count as Georgia Power is left to the
  overlap step.
- **Overrides replace the search; wrong points with no known answer are removed**
  (2026-09-26). A point in the wrong region (Hooks Pond, 180 mi from Hooks) would pull
  its project's center there, and inventing a location isn't allowed, so a blank
  override leaves the location with no point. Overrides with a point are rated HIGH, not
  a new label, because the summary ranks unknown labels below LOW. Wrong-named MEDIUM
  matches near the right place (16007, 20407) are left as they are.

## Process

- **Merge teammates' pull requests with a merge commit** (2026-09-26), so their
  commits keep their author.
- **Agent instructions live in `AGENTS.md`, and project knowledge in `docs/`**
  (2026-09-26). `AGENTS.md` is read by most coding agents, and `CLAUDE.md` imports it
  for Claude Code. The single `parser-handoff.md` was split into topic docs, so a
  session loads only what its task needs, and `tests/test_docs.py` keeps links and
  column lists in step with the code.
- **Made-up test data lives in `data/test/`, and a script cleans it** (2026-09-26).
  `data/processed/` holds only what our code produced from the PDFs, and the test DESC
  rows use the real DESC utility name, so mixing them would put fake projects into real
  overlaps. The teammate's originals are kept in `data/test/raw/` and fixed by
  `clean_test_csvs.py` rather than by hand, like the other generated CSVs.

## AI parser

- **An AI parser alongside the hand-written ones, not instead of them** (2026-09-26),
  so PDFs laid out differently don't each need a parser. The hand-written parsers stay
  as the reference its eval scores it against. Its output goes to `data/processed/ai/`,
  so nothing downstream switches to it until someone decides to.
- **The model only copies; Python checks and derives** (2026-09-26). Each value comes
  with its quote and page, and a value whose quote isn't on that page is left blank
  rather than trusted. That keeps "don't invent data": the main CSV has only values
  found in the PDF. Voltages, mileage and ID spelling are worked out in Python, with
  the hand-written parsers' rules.
- **Send pypdf's text, not the PDF** (2026-09-26). The checks compare against exactly
  what the model read, and it costs less than page images. A scanned PDF, or a table
  pypdf scrambles beyond use, would need page images instead.
- **Merge fragments on project ID; the earlier page wins, and a conflict is flagged**
  (2026-09-26). For Georgia Power that keeps Table 2's need date, as the hand-written
  parser does.
- **A second pass that lists only project IDs** (2026-09-26), with its chunk boundaries
  moved by half a chunk, to catch projects the extraction skipped. It costs about as
  much input as the extraction, and little output.
- **Cache every reply, keyed on everything that shaped it** (2026-09-26). Re-runs are
  free and reproducible (Opus 5 can't be made deterministic), and `--offline` rebuilds
  the CSV without a key. `pydantic` is pinned because the key includes its JSON schema.
- **`claude-opus-5` with adaptive thinking and effort `high` by default** (2026-09-26).
  A cheaper model or lower effort should be adopted only if it scores as well on the
  eval. The API's server-side fallback is on, so a declined request is retried on
  another model instead of stopping the run.
- **Each row's `utility` comes from its sponsor** (2026-09-26). Georgia Power's plan
  also lists GTC, MEAG and DU projects, so writing `--utility` on every row gave 70
  wrong (`utility`, `project_id`) keys. The AI parser uses the Georgia parser's own code
  table (`parsers/utilities.py`), so both produce the same keys. A missing or unknown
  sponsor goes to the review file instead of being guessed. The eval matches on the same
  key, so a wrong owner counts as a missing project.
- **DESC's banner `sponsor` is documented, not fixed** (2026-09-26). Fixing it means
  changing the prompt, which changes every cache key and needs a paid rerun. `utility`
  is right, and nothing downstream reads `sponsor`.

## Overlaps and the app

- **A project's center is the midpoint of `location_1` and `location_2`, or the one
  located point** (2026-09-26), not the Geolocator's centroid. It's the organizers'
  rule, and their sheet's distances reproduce to the hundredth with it. The centroid
  averages up to 4 points, LOW fallbacks included. See
  [app.md](app.md#centers-and-confidence).
- **Distance first, then timing, by default** (2026-09-26, chosen by Jair). The brief
  calls distance the primary signal and timing a strong secondary one
  ([challenge.md](challenge.md#goal)), so pairs are ordered by distance band (5, 15 and
  25 miles) before build windows and date gaps. The equal-weight score is kept as an
  option. See [app.md](app.md#overlaps-and-ranking).
- **A blank start date is open-ended only for DESC** (2026-09-26). DESC's blank means
  work began before 2024 (see [Parsing](#parsing)); another utility's blank is unknown,
  so its build-window overlap stays unknown rather than assumed.
- **The demo compares DESC with GPC and SAV** (2026-09-26), Georgia Power's own
  projects, as in the organizers' example. GTC, MEAG and DU are other utilities.
- **The app imports only the two organizer PDFs, matched by SHA-256** (2026-09-26).
  The saved points were checked for those exact plans, and a revised PDF's projects
  would need their locations reviewed again. The app makes no AI or geocoding calls,
  per AGENTS.md. See [app.md](app.md#pdf-uploads).
