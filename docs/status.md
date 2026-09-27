# Status

Where the work stands, what's next, and who owns what. Read this first, and update
it at the end of every work session (the
[handoff workflow](../.claude/skills/handoff/SKILL.md)). Durable facts belong in the
topic docs listed in [AGENTS.md](../AGENTS.md#where-knowledge-lives), not here.

Last updated 2026-09-27.

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
- **Geocoding** on `main` (https://github.com/jbear05/Shellhacks2026/pull/12, merged as
  eaacacc): both utilities are geocoded, with the outputs in `data/processed/desc_*` and
  `georgia_power_*` (all 208 Georgia projects, every sponsor) and no failed requests
  left. The Geolocator now downloads substations in cached 1° tiles, and
  `data/overrides/location_overrides.csv` holds 27 hand-checked fixes. What was checked,
  and what wasn't: [geolocator.md](geolocator.md#known-wrong-or-weak-lookups).
- **AI parser** on `main` (https://github.com/jbear05/Shellhacks2026/pull/7): reads any
  project-list PDF with Claude and checks every value against the page text. The
  outputs in `data/processed/ai/` were rebuilt from the committed cache, and
  `--offline` replays that cache with no key or credit. What's left is in
  [ai-parser.md](ai-parser.md#current-state).
- **Ranking script** on `main`: `ranking.py` scores overlap rows on distance, timeline
  overlap, days apart, voltage and project type, and can look up project CSVs by
  (`utility`, `project_id`); `tests/test_ranking.py` checks realistic pairs.
- **UI** on `main`: Nellie merged `origin/NA` into `main` without a pull request
  (5709833 and fd95a5e). The rework below replaced most of it. See
  [pipeline.md](pipeline.md#6-ui-frontend).
- **Test data** on `main` (https://github.com/jbear05/Shellhacks2026/pull/8 and
  https://github.com/jbear05/Shellhacks2026/pull/9): made-up DESC and Duke Energy
  Carolinas projects for testing the stages after the parsers. The originals are in
  `data/test/raw/`, and `clean_test_csvs.py` writes realigned copies to `data/test/`;
  see [data.md](data.md#datatest_test_projectscsv).
- **Real-data overlaps and the UI rework** on `main`
  (https://github.com/jbear05/Shellhacks2026/pull/14, with `fix/center-method-label`):
  5 commits made with Codex (e7ee917 to 2fce793). How the data side works is in
  [app.md](app.md).
  - `frontend/project_data.py` joins the parser CSVs to the Geolocator's `location_1`
    and `location_2` points on (`utility`, `project_id`): 44 DESC and 138 Georgia Power
    (GPC and SAV) projects.
  - `frontend/analysis.py` pairs them within 25 miles and ranks the pairs with the root
    `ranking.py`, which gained a `distance_first` mode. See
    [Overlap candidates](#overlap-candidates).
  - `frontend/pdf_import.py` reads the two organizer PDFs, recognized by their SHA-256,
    with the parsers and the saved points. It makes no AI or geocoding calls.
  - `frontend/data_loader.py` reads IDs as text, keeps each row's own utility, reads the
    Geolocator's and the Duke test file's coordinate columns, and recomputes centers.
  - 2fce793 rewrote the pages to use these modules, with an overview page, a map
    (`frontend/map_view.py`) and snapshot export and restore (`frontend/workspace.py`).
    Opened in a browser on 2026-09-27 on `fix/center-method-label` (see
    [Next steps](#next-steps) 1).
  - The Location Verification page ignores, with a warning, a center typed for a
    project whose center comes from its endpoints; it used to lower that project's
    confidence and then discard the edit. A center typed for a center-only project
    without one is now kept ([app.md](app.md#pdf-uploads)).
- **Missing endpoints** on `main` (PR #14, from `fix/center-method-label`, commits on
  `codex/finish-gridlock` from 347c1fd): a project naming two substations with only one
  located is labeled `one_of_two_endpoints`
  ([app.md](app.md#centers-and-confidence)), and overrides now locate VCS1, VCS2, Hooks,
  Coleman and Ritter, found by tracing OSM lines
  ([geolocator.md](geolocator.md#known-wrong-or-weak-lookups)). With them, 44 DESC and
  129 Georgia Power projects have a center, and there are 73 pairs (35 with overlapping
  build windows), or 53 without LOW-confidence centers. The overrides file has 29 rows.
  The Overlaps page's map now shows the substations behind each center.
- **Tests:** 236 pass and 2 files are skipped in the root `.venv` (227 fast, about
  15 s; the full suite about 40 s). The skipped files, `tests/test_app.py` and
  `tests/test_map_view.py`, need Streamlit and pydeck; their 6 tests pass with
  `.venv-ui`, the Codex session's git-ignored venv. `tests/test_app.py` pins the pair
  counts, so run it after any change to the overrides.
- **Cost and impact estimate:** `frontend/impact.py` calculates a static shared-corridor
  estimate, and the Overlaps page displays potential acres saved, estimated dollar
  savings and the assumptions for each flagged pair. See [pipeline.md](pipeline.md#5-cost-estimate-bonus).

## Next steps

In priority order. The two required deliverables, the interactive map with the overlaps
and the ranked list ([challenge.md](challenge.md#deliverables)), work on our data on
`main`.

1. **Finish checking the demo in a browser:** `python -m streamlit run app.py` from the
   repository root, with the UI's packages (`pip install -r frontend/requirements.txt`).
   The root `.venv` doesn't have them; the Codex session's git-ignored `.venv-ui` does.
   The map's basemap needs internet. Checked on 2026-09-27: the overview page's demo
   button, the Overlaps page's counts (182 projects, 173 centers, 73 pairs), and the map
   with a focused pair. Not checked: the setup, review, location and export pages, and
   the export page's three downloads. The rework replaced most of Nellie's and
   AaxHamm3r's UI code, which they hadn't reviewed when PR #14 merged; tell them.
2. **Then the two teammate branches on 2fce793:** Nellie's `PrettyWeb` (one styling
   commit; a trial merge with `fix/center-method-label` had no conflicts) and
   DavidCode's `Deebranch`. Review `Deebranch` first: it deletes 50 files from
   `data/ai_cache/`, which `--offline` replays, and changes `frontend/pdf_import.py` and
   `parsers/ai_parser/api.py` to add AI PDF import. Check that the app still makes no
   LLM calls while it runs. Not read yet.
3. **Check the evidence behind the top pairs** in
   [Overlap candidates](#overlap-candidates) before presenting them. Fix a wrong point in
   `data/overrides/location_overrides.csv`, as in
   [geolocator.md](geolocator.md#overrides), not in the UI. Ranks 2-5 use Hooks, whose
   evidence is line lengths, not a name.
4. **Demo the AI parser** with `--offline`, using the commands in
   [ai-parser.md](ai-parser.md#current-state). Georgia's cache covers only pages 171-440
   without the ID pass, so other Georgia runs send paid requests. The ID pass costs about
   $3 and needs approval; see the [ai-parse workflow](../.claude/skills/ai-parse/SKILL.md).
5. **Test with the made-up data.** The branch's loader gives all 100 Duke test rows a
   center. The DESC test file has no coordinates: geocode it with `--projects-csv` and
   `--output-prefix desc_test` (never the default prefix; see
   [data.md](data.md#datatest_test_projectscsv)). No page joins a geocoded file to its
   dates yet; `attach_locations()` in `frontend/project_data.py` does it for the real
   files.
6. Small: warn in `parsers/georgia_power.py` when `start_date` is after
   `in_service_date` (TEAMS 20248; the UI already flags it); stop extracting the Georgia
   PDF after its last detail page (saves about 1.5 s); remove the 3 LibreOffice lock
   files committed in `frontend/test_data/overlap_case/` (`.~lock.*#`) and ignore them
   in `.gitignore`.

## Branches

| Branch | Owner | State |
|---|---|---|
| `main` | | Parsers, AI parser, Geolocator and geocoded outputs, ranking, the real-data overlaps and reworked UI, test data, docs, tests, committed CSVs |
| `codex/finish-gridlock` | Jair, with Codex | Merged into `main` in PR #14; kept |
| `fix/center-method-label` | Jair, with Claude | Merged in PR #14; kept |
| `origin/PrettyWeb` | Nellie (teammate) | One commit, c697930 "style", on `codex/finish-gridlock`: `frontend/ui.py`, `frontend/app.py`, the overview page, `frontend/.streamlit/config.toml` and a font. Not merged; no files in common with `fix/center-method-label` |
| `origin/Deebranch` | DavidCode (teammate) | PR #13 open, at d8cc7e1, on `codex/finish-gridlock`: AI PDF import; see [Next steps](#next-steps) 2. Not merged |
| `docs/status-after-geocode` | Jair | Local, at `main` (eaacacc) with no commits of its own; can be deleted |
| `origin/feat/geocode` | Jair | Merged in PR #12 at eaacacc; kept |
| `origin/docs/status-update` | Jair | Merged in PR #11; kept (a sibling worktree, `../Shellhacks2026-sam`, has it checked out) |
| `origin/copilot/accept-two-pdfs-ai-parser` | A Copilot agent | PR #10, closed without merging by Jair ("Not going to be used"); can be deleted |
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
- **Many demo centers are LOW:** 21 of 44 DESC and 64 of 138 Georgia Power projects,
  because a project takes its weakest named endpoint's rating and an endpoint with no
  point counts as LOW ([app.md](app.md#centers-and-confidence)). 9 have no center:
  GA 19966, 20175, 20223, 20466, 20509, 20684, 20717, 20736 and 21093.
- **Weak lookups left on purpose:** 9 override rows leave a location with no point
  because the search was wrong and OSM has no substation with that name. One of them,
  DESC Riverport (a planned substation), could still change an overlap pair of
  06367 A-C, H. GA 16007 and 20407 have MEDIUM matches with other substations' names.
  See [geolocator.md](geolocator.md#known-wrong-or-weak-lookups).
- **Weak Georgia rows:** 2 `UNKNOWN` rows and 4 customer-project names; see
  [data.md](data.md#dataprocessedgeorgia_power_projectscsv).
- **Weak test rows:** 17 Duke test lines have endpoints more than twice their length
  apart, and some Duke coordinates are wrong; see
  [data.md](data.md#datatest_test_projectscsv).
- **Branches to delete** once nobody needs them: with PR #14 merged, every local branch
  is merged into `main` (check with `git branch --no-merged main`). On GitHub, the
  merged branches' copies can go, and so can `origin/copilot/accept-two-pdfs-ai-parser` (PR #10, closed),
  `origin/copilot/ranking-script-gridlock` (PR #6, closed) and
  `origin/copilot/research-ranking-categories` (no commits beyond `main`). Ask the
  owners before deleting `origin/NA`, `origin/Geolocator`, `origin/dominionScript` and
  `origin/sam_datasets`. Remove the clean sibling worktree `../Shellhacks2026-sam`
  before its branch, `docs/status-update`.

## Overlap candidates

From `frontend/analysis.py`, with LOW-confidence centers included. All 6 of the
organizers' example pairs
([challenge.md](challenge.md#the-organizers-example-answers)) are found, and their
negative projects (DESC 6807 B, GA 18492 and 11821) pair with nothing. Three
distances are within 0.21 miles of the sheet's: 6810 A - 20793 3.91, 06367 D-G -
20065 7.40 and 6808 S - 20065 14.60. 6809 E - 20793 is 4.40 against 8.01, because
the sheet has no Hooks point and ours does. The two with GA 20277 differ (8.38
against 5.65, and 13.13 against 14.34) because our 20277 includes a LOW Purrysburg
point (an unnamed 230 kV substation near Hardeeville), which the sheet doesn't have.

The top 5 of the default ranking:

| Rank | DESC | Georgia Power | Miles | Days apart | Build windows overlap | Confidence |
|---|---|---|---|---|---|---|
| 1 | 6810 O Urquhart - Aiken PSA | 16007 Fenwick Street - Sand Bar Ferry | 2.25 | 578 | No | Low, Medium |
| 2 | 6809 G Stevens Creek - Hooks | 20793 Evans Primary - Thurmond Dam #5 | 4.40 | 2709 | No | Medium, High |
| 3 | 6809 G Stevens Creek - Hooks | 20794 Evans Primary - Thurmond Dam #6 | 4.40 | 2709 | No | Medium, High |
| 4 | 6810 A Hooks - Thurmond | 20793 Evans Primary - Thurmond Dam #5 | 3.91 | 3074 | No | Medium, High |
| 5 | 6810 A Hooks - Thurmond | 20794 Evans Primary - Thurmond Dam #6 | 3.91 | 3074 | No | Medium, High |

- The DESC center of rank 1 is Urquhart alone, because Aiken PSA has no point. 16007's
  two MEDIUM points are customer substations about a mile from the named streets.
- Within a distance band, overlapping build windows and then the smaller date gap come
  first, which puts 6809 G (4.40 miles, 2709 days) above 6810 A (3.91 miles, 3074
  days).
- DESC 06367 A-C, H (Riverport Tap) has no Riverport point, so its center is Okatie
  alone.
