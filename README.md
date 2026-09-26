# Gridlock (ShellHacks 2026, Sperry Tech challenge)

Flag where Dominion Energy South Carolina and Georgia Power plan transmission work
within 25 miles of each other and in overlapping build windows. The challenge brief,
guide and source PDFs are in `Sperry-Tech-Challenge/`.

## Setup

Needs Python 3.11 or newer (pandas 3 won't install on older versions).

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Docs

- [docs/status.md](docs/status.md): what's done, what's next, and who owns which branch.
- [docs/data.md](docs/data.md): every column of every CSV, and how the files join.
- [docs/](docs/): the challenge, the pipeline, the two source PDFs, the Geolocator, and
  the decisions made so far.
- [AGENTS.md](AGENTS.md): instructions for AI coding agents (Claude Code reads it
  through [CLAUDE.md](CLAUDE.md)). It's also a quick tour of the repo for people.

## Georgia Power parser

```bash
python -m parsers.georgia_power                      # all sponsors
python -m parsers.georgia_power --sponsors GPC SAV   # Georgia Power's own projects only
```

Writes `data/processed/georgia_power_projects.csv`, one row per project in the
Ten-Year Plan inside `2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf`. It joins two parts of
the plan on TEAMS number:

- Table 2 (project list): name, zone, plan year, need date, sponsor.
- Section IV detail pages: start date, scope description, change since the last plan.

The run stops with an error if the PDF's structure no longer matches what the parser
expects (for example, row counts that don't reconcile). Problems in the source data
itself, such as 3 projects whose need date differs between Table 2 and their detail
page, are logged as warnings.

Locations, project type and voltages are guessed from the title, so check them before
geocoding. The columns are described in
[docs/data.md](docs/data.md#dataprocessedgeorgia_power_projectscsv).

## Dominion parser

```bash
python dominionScript.py
```

Writes `data/processed/dominion_projects.csv`, one row per page of
`2024-2028-2million-and-above-project-descriptions.pdf`, with the Georgia Power CSV's
column names and formats. Project IDs are spelled as in the Geolocator's project list,
which supplies the locations, project type and voltages. The columns are described in
[docs/data.md](docs/data.md#dataprocesseddominion_projectscsv).

## AI parser

This branch's implementation is work in progress and currently has failing tests and a
quote-matching regression. Start with the [AI parser handoff](docs/ai-parser.md#picking-up-this-branch)
before regenerating data; the successful saved CSVs predate the regression.

```bash
python -m parsers.ai_parser PDF --utility "Georgia Power" --state Georgia --prefix georgia_power_ai --dry-run
python -m parsers.ai_parser.evaluate data/processed/ai/georgia_power_ai_projects.csv data/processed/georgia_power_projects.csv
```

Reads the projects out of any utility project-list PDF with Claude, for PDFs that have
no parser of their own. The model copies each value along with the text and page it
came from, and a value whose text isn't on that page is left blank and listed in
`data/processed/ai/<prefix>_review.csv`. It needs an `ANTHROPIC_API_KEY` and costs
money, so start with `--dry-run`; replies are cached in `data/ai_cache/`. The eval
scores it against the hand-written parsers. See [docs/ai-parser.md](docs/ai-parser.md).

## Tests

```bash
pytest                 # everything; parses both real PDFs once (about 15 s)
pytest -m "not slow"   # skips the 668-page Georgia Power PDF (about 1 s)
```

## Geolocator

```bash
python gridlock_desc_locator.py   # the 44 DESC projects listed in the script
python gridlock_desc_locator.py --projects-csv data/processed/georgia_power_projects.csv --output-prefix georgia_power
```

Finds coordinates for each project's location names. Nominatim gives a general place,
then Overpass looks for OpenStreetMap substations within 25 km of it, scored on name,
operator, voltage and distance. It writes three files to `data/processed/`:

- `<prefix>_project_locations.csv`: one row per location.
- `<prefix>_projects_summary.csv`: one row per project, with the average of its points.
- `<prefix>_manual_review.csv`: every location not rated HIGH.

Join the outputs to a parser CSV on `utility` and `project_id`, reading IDs as text.
How it scores, what it caches and which lookups it gets wrong are in
[docs/geolocator.md](docs/geolocator.md).
