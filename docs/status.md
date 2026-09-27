# Status

Where the work stands, what's next, and who owns what. Read this first, and update
it at the end of every work session (the
[handoff workflow](../.claude/skills/handoff/SKILL.md)). Durable facts belong in the
topic docs listed in [AGENTS.md](../AGENTS.md#where-knowledge-lives), not here.

Last updated 2026-09-26.

## The AI parser branch

`feat/ai-parser` is ready for review. It holds a command-line parser that reads any
utility project-list PDF with Claude and writes a project CSV, with review and
evidence files alongside it. The regressions the
[review](ai-parser-review.md#where-each-finding-stands) found are fixed, the full suite
passes, and the outputs in `data/processed/ai/` were rebuilt from the committed cache.
What's left is in [ai-parser.md](ai-parser.md#current-state).

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
- **Tests:** 169 with the `sam_datasets` cleanup, 162 of them fast. The full suite takes
  20-50 s.
- **Ranking script:** `ranking.py` now ranks overlap CSV rows with distance, timeline
  overlap, days apart, power voltage and project type scores. It accepts project CSVs
  for enrichment by (`utility`, `project_id`); `tests/test_ranking.py` checks realistic
  pairs and prints their ranked output. UI integration is still open.
- **Test data** (https://github.com/jbear05/Shellhacks2026/pull/8, then a cleanup on
  `sam_datasets`): made-up DESC and Duke Energy Carolinas projects for testing the
  stages after the parsers. The originals are in `data/test/raw/`, and
  `clean_test_csvs.py` writes realigned copies to `data/test/`; see
  [data.md](data.md#datatest_test_projectscsv).

## Next steps

In rough priority order:

1. **AI parser:** review and merge `feat/ai-parser`
   (https://github.com/jbear05/Shellhacks2026/pull/7). After that, optionally finish
   Georgia's ID pass (about $3, and it needs approval) with the
   [ai-parse workflow](../.claude/skills/ai-parse/SKILL.md). The extraction already
   finds all 208 projects with the right owners, so the pass is only a cross-check.
2. **Geocode DESC.** No full run is committed yet. Consider deleting the 7 `null`
   Nominatim entries from the cache first; see [geolocator.md](geolocator.md#cache).
   Start with the [geocode workflow](../.claude/skills/geocode/SKILL.md).
3. **Geocode Georgia Power** (353 location slots) and review
   `data/processed/georgia_power_manual_review.csv`. Projects around Savannah and
   Augusta matter most.
4. **Overrides file** for the heuristics' and Geolocator's known mistakes; see
   [pipeline.md](pipeline.md#3-manual-overrides).
5. **Overlap finder**, tested against the organizers' 6 example overlaps; see
   [pipeline.md](pipeline.md#4-overlaps-planned).
6. **Wire ranking into the UI/export.** The current UI overlap export has names,
   distance and in-service dates but not IDs, voltage or project type, so pass a richer
   overlap table or project lookup into `ranking.py` first.
7. **UI.** Once the UI owners agree, bring `frontend/` onto a branch off `main` with
   `git cherry-pick fb1c0c3`. That keeps Nellie as the author, and only `.gitignore`
   should conflict. Then write a per-project table with coordinates that the upload
   page can map, and read IDs as text. See
   [pipeline.md](pipeline.md#6-ui-originna-not-merged).
8. **Cost estimate** (bonus); see [pipeline.md](pipeline.md#5-cost-estimate-bonus-planned).
9. Small: warn when `start_date` is after `in_service_date` (TEAMS 20248), and stop
   extracting the Georgia PDF after its last detail page (saves about 1.5 s).

## Branches

| Branch | Owner | State |
|---|---|---|
| `main` | | Parsers, Geolocator, agent docs, tests, committed CSVs |
| `origin/NA` | AaxHamm3r and Nellie (teammates) | Streamlit UI in `frontend/`; not merged, and shares no history with `main` (see Open issues) |
| `origin/Geolocator` | DavidCode (teammate); fixed by Jair | Merged in PR #3; kept |
| `origin/dominionScript` | thatsnotrlght (teammate); reworked by Jair | Merged in PR #2; kept |
| `sam_datasets` | thatsnotrlght (teammate); cleanup by Jair | Test CSVs merged in PR #8. The cleanup commit on top (`clean_test_csvs.py`, `data/test/`) isn't merged |
| `origin/feat/gpc-pdf-parser` | Jair | Merged in PR #1; kept |
| `origin/chore/repo-cleanup` | Jair | Merged in PR #4; kept |
| `origin/docs/ai-context` | Jair | Its two commits are in PR #4; kept |
| `feat/ai-parser` | Jair | AI parser, its tests, docs, `/ai-parse` workflow, cached replies and outputs. Review fixes are in and the full suite passes; ready to merge |

Check with a teammate before committing to their branch.

## Open issues

- **The API credit ran out** during the Georgia run on 2026-09-26, after about $5.40
  (DESC, a 4-page test and Georgia pages 171-440). The Georgia output in
  `data/processed/ai/georgia_power_ai_partial_*` was rebuilt from the cache without the
  ID pass.
- **The AI parser's DESC `sponsor`** is the page banner `Dominion Energy South Carolina`
  on all 44 rows, where `dominion_projects.csv` has `DESC`. `utility` is right. A prompt
  fix needs a paid run; see [ai-parser.md](ai-parser.md#scoring-it-the-eval).

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
