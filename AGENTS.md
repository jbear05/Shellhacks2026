# AGENTS.md

Instructions for AI coding agents (Claude Code, Codex, Cursor, Copilot, Gemini CLI
and others) working in this repository. People new to the repo can start with
[README.md](README.md), but everything here applies to them too.

## The project

Gridlock, the Sperry Tech challenge at ShellHacks 2026. Find where Dominion Energy
South Carolina (DESC) and Georgia Power plan transmission work within 25 miles of each
other (the main signal) and in overlapping build windows (secondary). Show the
results on an interactive map with a ranked list of coordination opportunities.
Details are in [docs/challenge.md](docs/challenge.md).

This is a hackathon project with four people working on separate branches. Prefer
small changes that are easy to check over large rewrites. Every number should stay
traceable to the source PDF.

## Start of every session

1. Read [docs/status.md](docs/status.md): what's done, what's next, open issues, and
   who owns which branch.
2. Read the doc for your task (see [Where knowledge lives](#where-knowledge-lives)).
   The docs hold what earlier sessions learned from the PDFs. Don't explore the
   668-page Georgia Power PDF again unless they don't answer your question.
3. Run the fast tests to confirm they pass before you change anything:
   `.venv/Scripts/python -m pytest -m "not slow"`.

## Commands

Run everything from the repository root. On macOS/Linux use `.venv/bin/python`.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt

.venv/Scripts/python -m pytest -m "not slow"    # about 1 s
.venv/Scripts/python -m pytest                  # 15-20 s; parses the 668-page PDF

.venv/Scripts/python -m parsers.georgia_power   # data/processed/georgia_power_projects.csv, 208 rows
.venv/Scripts/python dominionScript.py          # data/processed/dominion_projects.csv, 44 rows
.venv/Scripts/python clean_test_csvs.py         # data/test/*_test_projects.csv, made-up test projects

# Calls public Nominatim/Overpass servers and takes minutes. Read docs/geolocator.md first.
.venv/Scripts/python gridlock_desc_locator.py
.venv/Scripts/python gridlock_desc_locator.py --projects-csv data/processed/georgia_power_projects.csv --output-prefix georgia_power

# The AI parser calls the paid Claude API unless --dry-run or --offline. Read docs/ai-parser.md first.
.venv/Scripts/python -m parsers.ai_parser PDF --utility "..." --state "..." --prefix NAME --dry-run
.venv/Scripts/python -m parsers.ai_parser.evaluate data/processed/ai/NAME_projects.csv data/processed/dominion_projects.csv
```

## Repository map

| Path | What it is |
|---|---|
| `parsers/common.py` | Text helpers shared by both parsers: dashes, dates, kV, miles |
| `parsers/georgia_power.py` | The Georgia Power parser and its CLI |
| `parsers/ai_parser/` | The AI parser for any project-list PDF, its eval, and its reply cache logic (the cache is `data/ai_cache/`) |
| `dominionScript.py` | The DESC parser and its CLI (a teammate's file, kept at the root) |
| `gridlock_desc_locator.py` | The Geolocator: coordinates from Nominatim and Overpass |
| `gridlock_geocode_cache.json` | The Geolocator's request cache |
| `data/processed/` | Parser output, committed so teammates don't need Python, and the Geolocator's output |
| `data/test/` | Made-up test projects, not from the PDFs: a teammate's files in `raw/` and their cleaned copies |
| `clean_test_csvs.py` | Realigns the test CSVs in `data/test/raw/` and writes them to `data/test/` |
| `tests/` | pytest; the `slow` marker covers the tests that parse the 668-page PDF or load the Anthropic SDK |
| `docs/` | Project knowledge; see [Where knowledge lives](#where-knowledge-lives) |
| `.claude/skills/` | Step-by-step workflows in plain Markdown, usable by any agent |
| `Sperry-Tech-Challenge/` | The organizers' brief, guide, example sheet and source PDFs; read-only |
| `ranking.py` | Scores and orders overlap pairs; the UI uses its own copy, `frontend/ranking.py` |
| `frontend/` | The teammates' Streamlit UI; see [docs/pipeline.md](docs/pipeline.md#6-ui-frontend) |
| `app.py` | Empty. The UI's entry file is `frontend/app.py`, also empty |

## Pipeline

PDFs → parsers (or the AI parser) → `data/processed/*.csv` → Geolocator → `<prefix>_projects_summary.csv`
→ overlaps (only inside the UI) → UI (`frontend/`). What each stage reads and
writes, and the planned method for the unbuilt ones:
[docs/pipeline.md](docs/pipeline.md).

## Rules

- **Organizer files are read-only.** Never modify anything in `Sperry-Tech-Challenge/`.
- **Don't hand-edit generated CSVs.** Change the code, run it again, and commit the
  CSV together with the code that produced it.
- **Join on (`utility`, `project_id`), never on names.** Read IDs as text, because some
  start with 0 (pandas: `dtype=str, keep_default_na=False`).
- **Don't invent data.** A blank DESC `start_date` stays blank, and a LOW-confidence
  coordinate stays flagged. When the source contradicts itself, log a warning and
  don't fix it silently.
- **Fail loudly on structure, warn on data.** A parser raises and writes no CSV when
  the PDF's layout stops matching what it expects. Problems in the source data only
  log warnings. Keep it that way.
- **`pypdf` is pinned** because the regexes depend on its exact output. After changing
  the version, run both parsers again and explain every change in the CSVs.
- **No LLM calls at app runtime.** If an LLM ever fills in a fuzzy field, save its
  output to a file and check each value against the source text. The AI parser does
  both: it caches every reply and checks every value against the page it came from.
- **Public APIs:** keep the Geolocator at 1 request per second to Nominatim, and keep
  using its cache. Tests must never call the network. Ask before starting a full run.
- **The Claude API costs money.** Ask before running the AI parser without `--dry-run`
  or `--offline`, and say what `--dry-run` estimates. Never commit an API key.
- **Teammate branches:** don't commit to or push `origin/NA`, `origin/Geolocator` or
  `origin/dominionScript` unless the user has checked with the owner (listed in
  docs/status.md).
- **Git:** work on a branch off `main`, and commit or push only when asked. Merge
  teammates' pull requests with a merge commit so their commits keep their author.
  There is no CI, so run the full test suite before pushing.

## Conventions

- Python 3.11 or newer (pandas 3 needs it); the venv uses 3.12.
- `parsers/` uses type hints, dataclasses and `from __future__ import annotations`.
  The teammates' root scripts are plain procedural code. Match the file you're
  editing.
- Tests: unit tests on text samples copied from pypdf's output, and tests on the real
  PDFs. Every parser fix gets a test built from the page's real text.
- Commit messages: imperative and sentence case, with no prefix, for example
  "Cache Overpass results and report failed requests".
- Dates are ISO `YYYY-MM-DD`, voltages are in volts (`115000`), and distances are
  in miles.

## Known pitfalls

- `python parsers/georgia_power.py` fails to import. Use `python -m parsers.georgia_power`.
- The DESC PDF writes `06367 A - C, H`. The parser removes the spaces around `-` (but
  not around `,`), so IDs match the Geolocator's list exactly.
- Windows' 260-character path limit: a temp directory plus the long PDF names is too
  long, so `git worktree add` into a temp directory fails. A sibling folder of the
  repo works. To test one commit's code alone, extract it instead:
  `git archive <commit> parsers tests pyproject.toml | tar -x -C <dir>`.
- `core.autocrlf=true`, so the LF/CRLF warnings on commit are harmless.

## Where knowledge lives

Read the doc for your task, and write what you learn back into it.

| Topic | Doc |
|---|---|
| Status, next steps, open issues, branch owners | [docs/status.md](docs/status.md) |
| The brief, deliverables, target sheet, the organizers' example answers | [docs/challenge.md](docs/challenge.md) |
| Pipeline stages, their inputs and outputs, planned overlap and cost methods | [docs/pipeline.md](docs/pipeline.md) |
| Every CSV column, join keys, known weak rows | [docs/data.md](docs/data.md) |
| Georgia Power PDF layout | [docs/sources/georgia-power-pdf.md](docs/sources/georgia-power-pdf.md) |
| DESC PDF layout and project IDs | [docs/sources/dominion-pdf.md](docs/sources/dominion-pdf.md) |
| Geolocator search, scoring, cache, wrong lookups | [docs/geolocator.md](docs/geolocator.md) |
| AI parser: how it reads and checks, its eval, cost | [docs/ai-parser.md](docs/ai-parser.md) |
| Plan for connecting the UI to the parsers, Geolocator and ranking (not on `main` yet) | [docs/frontend-backend-integration-guide.md](docs/frontend-backend-integration-guide.md) |
| Why things are the way they are | [docs/decisions.md](docs/decisions.md) |

Keeping the docs useful:

- Put each fact in one place, and link to it instead of copying it.
- Update a doc in the same commit as the code change it describes.
- Only write numbers you've checked by running something, and say what you didn't
  check.
- `tests/test_docs.py` checks that relative links resolve and that docs/data.md lists
  every CSV column in order. A new column fails the tests until it's documented.

## Workflows

The step-by-step procedures are in `.claude/skills/`. Claude Code runs them as
`/name`; other agents can follow the SKILL.md file as written.

| Workflow | When |
|---|---|
| [handoff](.claude/skills/handoff/SKILL.md) | End of a session: update docs/status.md and the topic docs |
| [regenerate-data](.claude/skills/regenerate-data/SKILL.md) | After a parser change: run both parsers again, diff the CSVs, run the tests |
| [geocode](.claude/skills/geocode/SKILL.md) | Running the Geolocator and retrying failed requests |
| [ai-parse](.claude/skills/ai-parse/SKILL.md) | Running the AI parser on a PDF and scoring it against a hand-written parser |

## End of every session

Update docs/status.md (the handoff workflow). The next session, or a teammate, starts
from it with no other context.
