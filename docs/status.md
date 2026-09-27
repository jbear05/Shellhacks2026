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
  [geolocator.md](geolocator.md#cache).
- **Geocoding** (https://github.com/jbear05/Shellhacks2026/pull/12): both utilities
  are geocoded, with the outputs in `data/processed/desc_*` and `georgia_power_*` (all
  208 Georgia projects, every sponsor) and no failed requests left. The Geolocator now
  downloads substations in cached 1° tiles, and `data/overrides/location_overrides.csv`
  holds 27 hand-checked fixes. What was checked, and what wasn't:
  [geolocator.md](geolocator.md#known-wrong-or-weak-lookups).
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
- **Tests:** 170 on `main`, 163 of them fast; 205 with PR #12, 198 of them fast. The
  full suite takes 20-50 s.

## Next steps

In rough priority order. The plan is to demo the AI parser on the organizers' PDFs,
then test the later stages with the made-up CSVs in `data/test/`.

1. **Demo the AI parser** with `--offline`, using the commands in
   [ai-parser.md](ai-parser.md#current-state). Optionally finish Georgia's ID pass
   first (about $3, and it needs approval) with the
   [ai-parse workflow](../.claude/skills/ai-parse/SKILL.md). Running it from the UI
   (PR #10) doesn't use the offline mode. Georgia's cache covers only pages 171-440
   without the ID pass, so a full Georgia upload there would send paid requests (not
   tried).
2. **Review and merge the geocoding**
   (https://github.com/jbear05/Shellhacks2026/pull/12). It changes the teammates'
   Geolocator (`gridlock_desc_locator.py`), so DavidCode may want to look. Don't run
   the geocode again: the committed cache has every result.
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
5. **Check the overlaps against the organizers' 6 example pairs.** A quick check with
   their midpoint rule is done (see [Overlap candidates](#overlap-candidates)). The UI's
   overlaps page is the only pairing code so far; the planned standalone finder is in
   [pipeline.md](pipeline.md#4-overlaps-planned). Take centers from
   `<prefix>_project_locations.csv`, not the summary's centroid.
6. **More overrides**, only if the overlaps need them: most of both lists is unchecked.
   Add a row with its evidence, as in [geolocator.md](geolocator.md#overrides).
7. **Cost estimate** (bonus); see [pipeline.md](pipeline.md#5-cost-estimate-bonus-planned).
8. Small: warn when `start_date` is after `in_service_date` (TEAMS 20248); stop
   extracting the Georgia PDF after its last detail page (saves about 1.5 s); remove the
   3 LibreOffice lock files committed in `frontend/test_data/overlap_case/`
   (`.~lock.*#`) and ignore them in `.gitignore`.

## Branches

| Branch | Owner | State |
|---|---|---|
| `main` | | Parsers, AI parser, Geolocator, ranking, UI, test data, docs, tests, committed CSVs |
| `origin/feat/geocode` | Jair | PR #12, open: tile search, overrides, both utilities geocoded, tests. `main` is merged in, including PR #11 |
| `origin/docs/status-update` | Jair | Merged in PR #11; kept (a sibling worktree, `../Shellhacks2026-sam`, has it checked out) |
| `origin/copilot/accept-two-pdfs-ai-parser` | A Copilot agent | PR #10, open and not reviewed: the setup page takes one PDF per utility and runs the AI parser on it in a background thread. It builds the model with `offline=False`, so pages missing from the cache go to the paid API. Review it against the rules on runtime LLM calls and API cost in AGENTS.md |
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
- **Weak lookups left on purpose:** 12 location names have no point because the search
  was wrong and OSM has no substation with that name (for example DESC Hooks and
  Riverport, and GA Coleman, which could be either of two Savannah substations). GA
  16007 and 20407 have MEDIUM matches with other substations' names. See
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

The organizers' example lists 6 pairs
([challenge.md](challenge.md#the-organizers-example-answers)). With `feat/geocode`'s
coordinates and their rule (the midpoint of `location_1` and `location_2`, or the one
located point), all 6 are under 25 miles. Four are within 0.15 miles of the sheet's
distance. The two with GA 20277 differ (8.38 against 5.65, and 13.13 against 14.34)
because our 20277 includes a LOW Purrysburg point (an unnamed 230 kV substation near
Hardeeville), which the sheet doesn't have. From names and dates, also worth checking:

- GA 20794 Evans Primary - Thurmond Dam #6 (starts 2030-06-01), the twin of 20793.
  Both are due 2033-06-01, so their build windows don't overlap with DESC 6810 A
  (due 2024-12-31).
- DESC 06367 A-C, H Riverport Tap, next to 06367 D-G, against GA 20277, 20065 and
  20785 (Goshen - Kraft). 20277 runs 2024-01-01 to 2026-06-01, overlapping 06367's
  build (due 2025-12-31). Riverport has no point, so 06367 A-C, H's center is Okatie.
- Augusta-area DESC projects (6809 G Stevens Creek - Hooks, 6852 Urquhart - Toolebeck,
  6810 O Urquhart - Aiken PSA) against Georgia's Evans and Thomson projects (14222,
  17993), 16007 Fenwick Street - Sand Bar Ferry, and 21116. 21116 "Goshen area" is the
  Goshen in south Augusta, not Savannah's (GA PDF p. 382).
