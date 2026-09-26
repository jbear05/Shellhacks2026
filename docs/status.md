# Status

Where the work stands, what's next, and who owns what. Read this first, and update
it at the end of every work session (the
[handoff workflow](../.claude/skills/handoff/SKILL.md)). Durable facts belong in the
topic docs listed in [AGENTS.md](../AGENTS.md#where-knowledge-lives), not here.

Last updated 2026-09-26.

## Done

- **Georgia Power parser** on `main` (https://github.com/jbear05/Shellhacks2026/pull/1):
  `python -m parsers.georgia_power` writes `data/processed/georgia_power_projects.csv`,
  208 projects.
- **DESC parser** on `main` (https://github.com/jbear05/Shellhacks2026/pull/2):
  `python dominionScript.py` writes `data/processed/dominion_projects.csv`, 44
  projects, with IDs spelled as in the Geolocator's list.
- **Geolocator** on `main` (https://github.com/jbear05/Shellhacks2026/pull/3):
  `gridlock_desc_locator.py` works on the built-in DESC list or a parser CSV, and its
  output is keyed on (`utility`, `project_id`). The DESC list's 44 IDs match
  `dominion_projects.csv` exactly.
- **Tests:** 80 on `main`, 75 of them fast. With `tests/test_docs.py` (not merged)
  it's 99, 94 of them fast. They take 15-20 s in total.
- **Agent docs:** `AGENTS.md`, `CLAUDE.md`, `docs/`, `.claude/` and
  `tests/test_docs.py`, on branch `docs/ai-context`, in the `chore/repo-cleanup` pull
  request (not merged).

## Next steps

In rough priority order:

1. **Geocode DESC.** No full run is committed yet. Consider deleting the 7 `null`
   Nominatim entries from the cache first; see
   [geolocator.md](geolocator.md#cache).
2. **Geocode Georgia Power** (353 location slots) and review
   `data/processed/georgia_power_manual_review.csv`. Projects around Savannah and
   Augusta matter most.
3. **Overrides file** for the heuristics' and Geolocator's known mistakes; see
   [pipeline.md](pipeline.md#3-manual-overrides-planned).
4. **Overlap finder**, tested against the organizers' 6 example overlaps; see
   [pipeline.md](pipeline.md#4-overlaps-planned).
5. **UI:** merge `origin/NA` once its owner agrees (see its open issue below), and
   load the real project and location tables. Its latest commit, fb1c0c3, moved it
   into `frontend/` with its own `frontend/requirements.txt`;
   [pipeline.md](pipeline.md#6-ui-originna-not-merged) describes the version before
   that.
6. **Cost estimate** (bonus); see [pipeline.md](pipeline.md#5-cost-estimate-bonus-planned).
7. Small: warn when `start_date` is after `in_service_date` (TEAMS 20248), and stop
   extracting the Georgia PDF after its last detail page (saves about 1.5 s).

## Branches

| Branch | Owner | State |
|---|---|---|
| `main` | | Parsers, Geolocator, tests, committed CSVs |
| `origin/NA` | AaxHamm3r (teammate); fb1c0c3 by Nellie | Streamlit UI in `frontend/`; not merged |
| `origin/Geolocator` | DavidCode (teammate); fixed by Jair | Merged in PR #3; kept |
| `origin/dominionScript` | thatsnotrlght (teammate); reworked by Jair | Merged in PR #2; kept |
| `origin/feat/gpc-pdf-parser` | Jair | Merged in PR #1; kept |
| `chore/repo-cleanup` | Jair | Built on `docs/ai-context`. Removes the Geolocator's draft scripts and partial output, and fixes its cache and paths. Pull request to `main`, not merged |
| `docs/ai-context` | Jair | The agent docs. Local only; its commits are in `chore/repo-cleanup` |

Check with a teammate before committing to their branch.

## Open issues

- **Project centers** average every located point, LOW fallbacks included, which
  isn't the organizers' two-point midpoint. Decide before building the overlaps.
- **Wrong lookups:** `EVANS PRIMARY` and `MCINTOSH` find counties; see
  [geolocator.md](geolocator.md#known-wrong-or-weak-lookups).
- **Weak Georgia rows:** 2 `UNKNOWN` rows and 4 customer-project names; see
  [data.md](data.md#dataprocessedgeorgia_power_projectscsv).
- **`origin/NA` deletes `Sperry-Tech-Challenge/`** in fb1c0c3: the brief, the example
  sheet and both source PDFs. Merged as it is, that removes the parsers' inputs, and
  the tests on the real PDFs are skipped instead of failing. Ask the owner to restore
  the folder before it's merged.
- **`origin/NA` reads CSVs with pandas defaults** (`frontend/data_loader.py`), which
  turns TEAMS `09662` into `9662`; see [data.md](data.md#reading-the-csvs).
- **`app.py` is empty** on `main`. `origin/NA` moves it, still empty, to
  `frontend/app.py`. Ask the UI owner whether it's needed.
- **Merged local branches** (`Geolocator`, `dominionScript`, `feat/gpc-pdf-parser`)
  could be deleted.

## Overlap candidates

Not geocoded yet. The organizers' example already lists 6 pairs
([challenge.md](challenge.md#the-organizers-example-answers)). From names and dates,
also worth checking:

- GA 20794 Evans Primary - Thurmond Dam #6 (starts 2030-06-01), the twin of 20793.
  Both are due 2033-06-01, so their build windows don't overlap with DESC 6810 A
  (due 2024-12-31).
- DESC 06367 A-C, H Riverport Tap, next to 06367 D-G, against GA 20277, 20065, 20785
  (Goshen - Kraft) and 21116 (Goshen area). 20277 runs 2024-01-01 to 2026-06-01,
  overlapping 06367's build (due 2025-12-31).
- Augusta-area DESC projects (6809 G Stevens Creek - Hooks, 6852 Urquhart - Toolebeck,
  6810 O Urquhart - Aiken PSA) against Georgia's Evans and Thomson projects (14222,
  17993).
