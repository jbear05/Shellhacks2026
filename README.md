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
pip install -r frontend/requirements.txt
python -m streamlit run app.py
```

Choose **Explore the real-data demo** to load DESC and Georgia Power with saved
geocoding. Project Setup also accepts the two organizer PDFs directly, CSV/XLSX
project tables, or an exported snapshot ZIP. No paid AI or geocoding calls run in
the app. See [the app guide](docs/app.md) for centers, confidence, ranking and export
behavior. The map's basemap needs internet access; computation uses local data.

## Docs

- [docs/status.md](docs/status.md): what's done, what's next, and who owns which branch.
- [docs/data.md](docs/data.md): every column of every CSV, and how the files join.
- [docs/](docs/): the challenge, the pipeline, the two source PDFs, the Geolocator, and
  the decisions made so far.
- [AGENTS.md](AGENTS.md): instructions for AI coding agents (Claude Code reads it
  through [CLAUDE.md](CLAUDE.md)). It's also a quick tour of the repo for people.

## Processed project data

The frontend's known-PDF importer reads the committed project tables in
`data/processed/` rather than running a utility-specific parser at upload time. The
tables preserve the project fields used by the Geolocator and the frontend; their
columns and provenance are documented in [docs/data.md](docs/data.md).

## AI parser

```bash
python -m parsers.ai_parser PDF --utility "Georgia Power" --state Georgia --prefix georgia_power_ai --dry-run
python -m parsers.ai_parser.evaluate data/processed/ai/georgia_power_ai_projects.csv data/processed/georgia_power_projects.csv
```

Reads project data from utility project-list PDFs with Claude. The model copies each
value along with the text and page it
came from, and a value whose text isn't on that page is left blank and listed in
`data/processed/ai/<prefix>_review.csv`. It needs an `ANTHROPIC_API_KEY` and costs
money, so start with `--dry-run`; replies are cached in `data/ai_cache/`, and
`--offline` rebuilds saved outputs from the cache for free. See
[docs/ai-parser.md](docs/ai-parser.md).

## Tests

```bash
pytest                 # all tests
pytest -m "not slow"   # skips tests marked slow
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
