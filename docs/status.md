# Status

Where the work stands, what's next, and who owns what. Read this first, and update
it at the end of every work session (the
[handoff workflow](../.claude/skills/handoff/SKILL.md)). Durable facts belong in the
topic docs listed in [AGENTS.md](../AGENTS.md#where-knowledge-lives), not here.

Last updated 2026-09-26, evening.

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
  `tests/test_docs.py`. The Geolocator now retries failed Nominatim lookups, saves its
  cache safely, and writes its outputs to `data/processed/`; see
  [geolocator.md](geolocator.md#cache). It has no automated tests on `main`, and no
  live run of these fixes is committed yet.
- **AI parser** on `main` (https://github.com/jbear05/Shellhacks2026/pull/7): reads any
  project-list PDF with Claude and checks every value against the page text. The
  outputs in `data/processed/ai/` were rebuilt from the committed cache, and
  `--offline` replays that cache with no key or credit. What's left is in
  [ai-parser.md](ai-parser.md#current-state).
- **Ranking script:** `ranking.py` scores overlap rows on distance, timeline overlap,
  days apart, voltage and project type, and can look up project CSVs by (`utility`,
  `project_id`); `tests/test_ranking.py` checks realistic pairs.
- **UI** on `main`: Nellie merged `origin/NA` into `main` without a pull request
  (5709833 and fd95a5e). The overlaps page pairs projects within the distance threshold
  and ranks them with its own `frontend/ranking.py`. See
  [pipeline.md](pipeline.md#6-ui-frontend).
- **Test data** on `main` (https://github.com/jbear05/Shellhacks2026/pull/8 and
  https://github.com/jbear05/Shellhacks2026/pull/9): made-up DESC and Duke Energy
  Carolinas projects for testing the stages after the parsers. The originals are in
  `data/test/raw/`, and `clean_test_csvs.py` writes realigned copies to `data/test/`;
  see [data.md](data.md#datatest_test_projectscsv).
- **Tests:** 170 on `main`, 163 of them fast. The full suite takes 20-50 s.

## Next steps

In rough priority order. The plan is to demo the AI parser on the organizers' PDFs,
then test the later stages with the made-up CSVs in `data/test/`.

1. **Demo the AI parser** with `--offline`, using the commands in
   [ai-parser.md](ai-parser.md#current-state). Optionally finish Georgia's ID pass
   first (about $3, and it needs approval) with the
   [ai-parse workflow](../.claude/skills/ai-parse/SKILL.md).
2. **Geocode DESC and Georgia Power.** In progress on the local `feat/geocode` branch,
   in another session, with no outputs committed when this was written; check that
   branch before starting. Start with the
   [geocode workflow](../.claude/skills/geocode/SKILL.md). For Georgia, review
   `data/processed/georgia_power_manual_review.csv`; projects around Savannah and
   Augusta matter most.
3. **Connect the UI to our data.** AaxHamm3r's plan is
   [frontend-backend-integration-guide.md](frontend-backend-integration-guide.md): one
   project schema, centers from the two endpoints, the root `ranking.py`, in five
   phases, starting with its section 17. None of it is on `main` yet. The quickest fix for a
   demo is to add `centroid_latitude`/`centroid_longitude` and the test file's
   `center_lat`/`center_lon` to `COLUMN_ALIASES` in `frontend/data_loader.py`, and to
   read IDs as text. It's the UI owners' code, so agree the approach with Nellie and
   AaxHamm3r. See [pipeline.md](pipeline.md#6-ui-frontend).
4. **Test with the made-up data:** geocode `data/test/desc_test_projects.csv` with
   `--projects-csv` and `--output-prefix desc_test` (never the default prefix; see
   [data.md](data.md#datatest_test_projectscsv)), then upload it and
   `duke_test_projects.csv` to the UI as DESC and Duke. Needs step 3.
5. **Overrides file** for the heuristics' and Geolocator's known mistakes; see
   [pipeline.md](pipeline.md#3-manual-overrides-planned). The Geolocator's support for
   `data/overrides/location_overrides.csv` is in commit 6d9264b on the local
   `feat/geocode` branch, not pushed yet.
6. **Check the overlaps against the organizers' 6 example pairs** once both utilities
   are geocoded. The UI's overlaps page is the only pairing code so far; the planned
   standalone finder is in [pipeline.md](pipeline.md#4-overlaps-planned).
7. **Cost estimate** (bonus); see [pipeline.md](pipeline.md#5-cost-estimate-bonus-planned).
8. Small: warn when `start_date` is after `in_service_date` (TEAMS 20248); stop
   extracting the Georgia PDF after its last detail page (saves about 1.5 s); remove the
   3 LibreOffice lock files committed in `frontend/test_data/overlap_case/`
   (`.~lock.*#`) and ignore them in `.gitignore`.

## Branches

| Branch | Owner | State |
|---|---|---|
| `main` | | Parsers, AI parser, Geolocator, ranking, UI, test data, docs, tests, committed CSVs |
| `feat/geocode` | Jair (another session) | Local only, not pushed. One commit, 6d9264b: the Geolocator downloads substations in 1-degree tiles and applies `data/overrides/location_overrides.csv`, with tests. More geocoding work is uncommitted in the main checkout |
| `origin/copilot/accept-two-pdfs-ai-parser` | A Copilot agent | One commit adding `frontend/ai_parser_jobs.py` and changing the setup page, apparently to run the AI parser on uploaded PDFs. No pull request; not reviewed |
| `origin/NA` | AaxHamm3r and Nellie (teammates) | Merged into `main` at e9e14cc; kept |
| `origin/Geolocator` | DavidCode (teammate); fixed by Jair | Merged in PR #3; kept |
| `origin/dominionScript` | thatsnotrlght (teammate); reworked by Jair | Merged in PR #2; kept |
| `origin/sam_datasets` | thatsnotrlght (teammate); cleanup by Jair | Merged in PR #8 and PR #9; kept |
| `origin/feat/ai-parser` | Jair | Merged in PR #7; kept |
| `origin/feat/gpc-pdf-parser` | Jair | Merged in PR #1; kept |
| `origin/chore/repo-cleanup` | Jair | Merged in PR #4; kept |
| `origin/docs/ai-context` | Jair | Its two commits are in PR #4; kept |

Check with a teammate before committing to their branch.

## Open issues

- **The API credit ran out** during the Georgia run on 2026-09-26, after about $5.40
  (DESC, a 4-page test and Georgia pages 171-440). The Georgia output in
  `data/processed/ai/georgia_power_ai_partial_*` was rebuilt from the cache without the
  ID pass.
- **The AI parser's DESC `sponsor`** is the page banner `Dominion Energy South Carolina`
  on all 44 rows, where `dominion_projects.csv` has `DESC`. `utility` is right. A prompt
  fix needs a paid run; see [ai-parser.md](ai-parser.md#scoring-it-the-eval).
- **The UI can't show our data yet:** none of our files gives it coordinates (0 of the
  100 Duke test rows get a `Latitude`), and reading with pandas defaults turns TEAMS
  `09662` into `9662`. See [pipeline.md](pipeline.md#6-ui-frontend).
- **Two ranking scripts:** the UI ranks with `frontend/ranking.py`, a shorter copy of
  the root `ranking.py`, so a change to one doesn't reach the other. The integration
  guide recommends keeping the root one
  ([section 10](frontend-backend-integration-guide.md#10-use-one-ranking-implementation)).
- **Project centers** average every located point, LOW fallbacks included, which
  isn't the organizers' two-point midpoint. The integration guide proposes the midpoint
  of the two endpoints
  ([section 8](frontend-backend-integration-guide.md#8-calculate-center-points-correctly)).
  Decide before trusting the overlaps.
- **Wrong lookups:** `EVANS PRIMARY` and `MCINTOSH` find counties; see
  [geolocator.md](geolocator.md#known-wrong-or-weak-lookups).
- **Weak Georgia rows:** 2 `UNKNOWN` rows and 4 customer-project names; see
  [data.md](data.md#dataprocessedgeorgia_power_projectscsv).
- **Weak test rows:** 17 Duke test lines have endpoints more than twice their length
  apart, and some Duke coordinates are wrong; see
  [data.md](data.md#datatest_test_projectscsv).
- **`app.py` is empty** on `main`, and `frontend/app.py`, the UI's entry file, is empty
  too. Ask the UI owners whether the root one is needed.
- **Branches to delete** once nobody needs them: the merged local branches
  (`Geolocator`, `dominionScript`, `feat/gpc-pdf-parser`, `chore/repo-cleanup`,
  `docs/ai-context`, `docs/status-refresh`, `feat/ai-parser`) and their GitHub copies,
  `origin/copilot/ranking-script-gridlock` (PR #6, closed) and
  `origin/copilot/research-ranking-categories` (no commits beyond `main`). The sibling
  worktree `../Shellhacks2026-sam` can go too once its branch is committed.

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
