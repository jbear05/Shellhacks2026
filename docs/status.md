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
- **Agent docs and cleanup** on `main` (https://github.com/jbear05/Shellhacks2026/pull/4):
  `AGENTS.md`, `CLAUDE.md`, `docs/`, the `.claude/` skills and settings, and
  `tests/test_docs.py`. The Geolocator's draft scripts and partial output were removed.
  The Geolocator now retries failed Nominatim lookups, saves its cache safely, and
  writes its outputs to `data/processed/`; see [geolocator.md](geolocator.md#cache). It
  has no automated tests, and these fixes haven't had a live run yet.
- **Tests:** 99 on `main`, 94 of them fast. They take 15-20 s in total.

## Next steps

In rough priority order:

1. **Geocode DESC.** No full run is committed yet. Consider deleting the 7 `null`
   Nominatim entries from the cache first; see [geolocator.md](geolocator.md#cache).
   Start with the [geocode workflow](../.claude/skills/geocode/SKILL.md).
2. **Geocode Georgia Power** (353 location slots) and review
   `data/processed/georgia_power_manual_review.csv`. Projects around Savannah and
   Augusta matter most.
3. **Overrides file** for the heuristics' and Geolocator's known mistakes; see
   [pipeline.md](pipeline.md#3-manual-overrides-planned).
4. **Overlap finder**, tested against the organizers' 6 example overlaps; see
   [pipeline.md](pipeline.md#4-overlaps-planned).
5. **UI.** Once the UI owners agree, bring `frontend/` onto a branch off `main` with
   `git cherry-pick fb1c0c3`. That keeps Nellie as the author, and only `.gitignore`
   should conflict. Then write a per-project table with coordinates that the upload
   page can map, and read IDs as text. See
   [pipeline.md](pipeline.md#6-ui-originna-not-merged).
6. **Cost estimate** (bonus); see [pipeline.md](pipeline.md#5-cost-estimate-bonus-planned).
7. Small: warn when `start_date` is after `in_service_date` (TEAMS 20248), and stop
   extracting the Georgia PDF after its last detail page (saves about 1.5 s).

## Branches

| Branch | Owner | State |
|---|---|---|
| `main` | | Parsers, Geolocator, agent docs, tests, committed CSVs |
| `origin/NA` | AaxHamm3r and Nellie (teammates) | Streamlit UI in `frontend/`; not merged, and shares no history with `main` (see Open issues) |
| `origin/Geolocator` | DavidCode (teammate); fixed by Jair | Merged in PR #3; kept |
| `origin/dominionScript` | thatsnotrlght (teammate); reworked by Jair | Merged in PR #2; kept |
| `origin/feat/gpc-pdf-parser` | Jair | Merged in PR #1; kept |
| `origin/chore/repo-cleanup` | Jair | Merged in PR #4; kept |
| `origin/docs/ai-context` | Jair | Its two commits are in PR #4; kept |

Check with a teammate before committing to their branch.

## Open issues

- **`origin/NA` shares no history with `main`.** It was force-pushed as a single
  commit with no parent (fb1c0c3, Nellie, 2026-09-26 12:56) holding only `.gitignore`
  and `frontend/`. GitHub reports "No common ancestor between main and NA", so it can't
  open a normal pull request. Compared with `main`, the branch seems to delete
  `Sperry-Tech-Challenge/` and the parsers, but only because they were never in its
  history. A merge wouldn't remove them; replacing `main` with it would. The branch's
  earlier commits (tip e2f8e94, by AaxHamm3r) are no longer on any GitHub branch, but
  clones that fetched them still have them. Reworked versions of their five pages are
  in `frontend/pages/`.
- **The UI can't show our data yet:** it has no alias for the Geolocator's
  `centroid_*` columns, and reading with pandas defaults turns TEAMS `09662` into
  `9662`. See [pipeline.md](pipeline.md#6-ui-originna-not-merged).
- **Project centers** average every located point, LOW fallbacks included, which
  isn't the organizers' two-point midpoint. Decide before building the overlaps.
- **Wrong lookups:** `EVANS PRIMARY` and `MCINTOSH` find counties; see
  [geolocator.md](geolocator.md#known-wrong-or-weak-lookups).
- **Weak Georgia rows:** 2 `UNKNOWN` rows and 4 customer-project names; see
  [data.md](data.md#dataprocessedgeorgia_power_projectscsv).
- **`app.py` is empty** on `main`, and `frontend/app.py`, the UI's entry file, is empty
  too. Ask the UI owners whether the root one is needed.
- **Merged local branches** (`Geolocator`, `dominionScript`, `feat/gpc-pdf-parser`,
  `chore/repo-cleanup`, `docs/ai-context`) could be deleted, along with their copies on
  GitHub once nobody needs them.

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
