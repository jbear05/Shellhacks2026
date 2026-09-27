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
- **Nellie's styling** (`PrettyWeb`) on `main`: Nellie merged it without a pull request
  (20dc8d0), after PR #14.
- **Distance circles and the bonus estimate** on `main` in
  https://github.com/jbear05/Shellhacks2026/pull/15 (`radius-lines-map`, thatsnotrlght's
  commit a0ac1ef, fixed up by Jair with Claude and Codex), merged as 0d7bea3.
  The Overlaps map shades circles
  with a radius of half the threshold around paired centers
  ([app.md](app.md#centers-and-confidence)). The commit as pushed imported a module it
  didn't include and crashed when a pair was focused; the fix-up kept `main`'s map and
  dropped two demo scripts that matched every DESC project to Okatie.
- **The bonus estimate** (`frontend/impact.py`), in PR #15: the land two paired lines
  could save in one corridor, from the plans' line miles, GTC's easement widths and
  USDA's 2026 land values; 25 of the 73 demo pairs get one
  ([pipeline.md](pipeline.md#5-cost-and-impact-estimate-bonus)). It replaces two
  estimates: PR #15's footprint rule and Nellie's corridor cost (19ba174, pushed to
  `main` without a pull request), which used the distance between projects as the
  shared length ([decisions.md](decisions.md)).
- **PR #15 review:** the local merge of `main` and the existing shared-corridor
  fix were retained on `codex/review-pr-15`. The source references now link to their
  PDFs, and the UI explains that farm real estate values include buildings. Regression
  checks cover invalid lengths/voltages, a focused pair with no estimate, and
  6810 A / 20793 displaying 27.9 acres and $137,303. Fixes were pushed as 169b7a3;
  PR #15 merged with a merge commit on 2026-09-27.
- **PR #13 PDF import** on `main` (https://github.com/jbear05/Shellhacks2026/pull/13,
  merged as 97a016f): an exact organizer PDF loads its checked committed parser table
  and saved endpoint evidence. The review restored both deterministic parsers and their
  tests, kept all 55 reply-cache files, and removed the duplicate real-DESC `desc_test`
  outputs. The new programmatic AI helper is offline-only and outside the app. Both
  uploads match the saved demo field for field; the DESC helper replayed 44 projects
  and Georgia's offline CLI replayed 208 entirely from cache. See [app.md](app.md#pdf-uploads)
  and [ai-parser.md](ai-parser.md#current-state).
- **Demo checked in a browser** on 2026-09-27 (08:10 EDT, `main` at e4b2ad2, the root
  launch): all five pages open with no errors or server warnings. Overlaps shows 182
  projects, 173 centers, 73 pairs and 35 overlapping windows; Location Verification
  shows 85 LOW. The export page's three files were built in code from the same demo
  state: the snapshot ZIP restores to the same 73 ranked pairs, and 25 pairs carry a
  land estimate. Not checked in the browser: uploading PDFs, tables or a snapshot (the
  browser pane can't upload files; `tests/test_pdf_import.py` and
  `tests/test_workspace.py` cover them), and clicking the download buttons.
- **Fonts fixed** on `main` (https://github.com/jbear05/Shellhacks2026/pull/16): Nellie's Aeonik font never loaded,
  from either launch directory, because its URL lacked `app/`; the root launch now
  serves it too ([pipeline.md](pipeline.md#6-ui-frontend)). The 3 LibreOffice lock files
  in `frontend/test_data/overlap_case/` are removed and ignored.
- **The `score` ranking is the default** on `main`
  (https://github.com/jbear05/Shellhacks2026/pull/18, 2026-09-27, chosen by Jair;
  [decisions.md](decisions.md#overlaps-and-the-app)). The app starts
  with it and the demo button selects it, and the Overlaps page's caption now
  describes whichever ranking is selected. `distance_first` is still on
  the "Ranking policy" menu, and a snapshot keeps the mode it was saved with.
- **Tests:** 250 pass and 2 files are skipped in the root `.venv` (full suite,
  28.24 s on 2026-09-27). The skipped files, `tests/test_app.py` and
  `tests/test_map_view.py`, need Streamlit and pydeck; their 7 tests pass with
  `.venv-ui` (23.54 s), including review, location, export and focused-estimate flows
  through AppTest. No live browser check was made during the PR #13 review.
  `tests/test_app.py` pins the pair counts, so run it after changes to the overrides.

## Next steps

In priority order. The two required deliverables, the interactive map with the overlaps
and the ranked list ([challenge.md](challenge.md#deliverables)), work on our data on
`main`.

1. **Run the demo:** `python -m streamlit run app.py` from the repository root, with
   the UI's packages (`pip install -r frontend/requirements.txt`). The root `.venv`
   doesn't have them; the Codex session's git-ignored `.venv-ui` does. The map's
   basemap needs internet. Every page was checked on 2026-09-27 (see [Done](#done)).
   The rework replaced most of Nellie's and AaxHamm3r's UI code, which they hadn't
   reviewed when PR #14 merged; tell them, and tell Nellie that her fonts now load.
2. **Know the caveats behind the top pairs** of the `score` ranking, the default since
   2026-09-27, before presenting them; see [Overlap candidates](#overlap-candidates).
   Ranks 1 and 2 share GA 20277, whose center includes a LOW point, and rank 2's DESC
   center is one substation. Fix a wrong point in
   `data/overrides/location_overrides.csv`, as in
   [geolocator.md](geolocator.md#overrides), not in the UI.
3. **Demo the AI parser** with `--offline`, using the commands in
   [ai-parser.md](ai-parser.md#current-state). Georgia's cache covers only pages 171-440
   without the ID pass, so other Georgia runs send paid requests. The ID pass costs about
   $3 and needs approval; see the [ai-parse workflow](../.claude/skills/ai-parse/SKILL.md).
4. **Test with the made-up data.** The branch's loader gives all 100 Duke test rows a
   center. The DESC test file has no coordinates: geocode it with `--projects-csv` and
   `--output-prefix desc_test` (never the default prefix; see
   [data.md](data.md#datatest_test_projectscsv)). No page joins a geocoded file to its
   dates yet; `attach_locations()` in `frontend/project_data.py` does it for the real
   files.
5. Small: warn in `parsers/georgia_power.py` when `start_date` is after
   `in_service_date` (TEAMS 20248; the UI already flags it); stop extracting the Georgia
   PDF after its last detail page (saves about 1.5 s). On a narrow window (about 800
   pixels) the overview's and Overlaps page's metric labels are cut off ("Timi…"); they
   fit at 1440 pixels.

## Branches

| Branch | Owner | State |
|---|---|---|
| `main` | | Parsers, AI parser, Geolocator and geocoded outputs, ranking, the real-data overlaps and reworked UI, distance circles and shared-corridor estimate (PR #15), exact-PDF imports from committed tables (PR #13), test data, docs, tests, committed CSVs |
| `feat/score-ranking-default` | Jair, with Claude | Merged into `main` in https://github.com/jbear05/Shellhacks2026/pull/18 (the `score` ranking as the default); kept |
| `fix/demo-fonts-and-cleanup` | Jair, with Claude | Merged into `main` in https://github.com/jbear05/Shellhacks2026/pull/16 (the font fix, the lock-file cleanup and the final demo check); kept |
| `codex/finish-gridlock` | Jair, with Codex | Merged into `main` in PR #14; kept |
| `fix/center-method-label` | Jair, with Claude | Merged in PR #14; kept |
| `origin/PrettyWeb` | Nellie (teammate) | Merged into `main` by Nellie at 20dc8d0, without a pull request; kept |
| `origin/radius-lines-map` | thatsnotrlght (teammate); fixed up by Jair | Merged into `main` in PR #15 at 0d7bea3; kept |
| `codex/review-pr-15` | Jair, with Codex | PR #15 fixes merged; local checkout includes the merge and its handoff notes |
| `origin/Deebranch` | DavidCode (teammate); reviewed by Codex | Merged into `main` in PR #13 at 97a016f; kept |
| `codex/review-pr-13` | Jair, with Codex | PR #13 fixes merged; local checkout includes the merge and handoff notes |
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

The top 5 of the default `score` ranking (all have overlapping build windows):

| Rank | DESC | Georgia Power | Miles | Days apart | Confidence | Score |
|---|---|---|---|---|---|---|
| 1 | 06367 D-G Jasper - Okatie 230 kV #2 | 20277 McIntosh - Purrysburg 230kV reactors | 8.38 | 152 | High, Low | 13 |
| 2 | 06367 A-C, H Riverport Tap | 20277 McIntosh - Purrysburg 230kV reactors | 9.61 | 152 | Low, Low | 13 |
| 3 | 6852 Urquhart - Toolebeck 115kV | 16007 Fenwick Street - Sand Bar Ferry | 9.72 | 72 | High, Medium | 13 |
| 4 | 6809 G Stevens Creek - Hooks | 16007 Fenwick Street - Sand Bar Ferry | 14.88 | 152 | Medium, Medium | 13 |
| 5 | 6808 S Okatie-Bluffton 115kV | 20067 Deptford - Magnolia 115kV | 18.08 | 0 | High, High | 13 |

- Rank 1 is the organizers' OVL_2. Its distance, 8.38 miles against the sheet's 5.65,
  comes from 20277's LOW Purrysburg point (above); both are in the 5-15 mile band, so
  the score doesn't depend on that point.
- Rank 2's DESC center is Okatie alone, because Riverport (a planned substation) has
  no point. Rank 4 uses Hooks, whose evidence is line lengths, not a name.
- Rank 3's 16007 points are customer substations about a mile from the named streets
  (see below); 9.72 miles stays in the 5-15 mile band unless the center is off by
  more than 4.7 miles.
- Ties at the same score go to the closer pair.

The top 5 of the `distance_first` ranking (the default until 2026-09-27; none of
their build windows overlap):

| Rank | DESC | Georgia Power | Miles | Days apart | Build windows overlap | Confidence |
|---|---|---|---|---|---|---|
| 1 | 6810 O Urquhart - Aiken PSA | 16007 Fenwick Street - Sand Bar Ferry | 2.25 | 578 | No | Low, Medium |
| 2 | 6809 G Stevens Creek - Hooks | 20793 Evans Primary - Thurmond Dam #5 | 4.40 | 2709 | No | Medium, High |
| 3 | 6809 G Stevens Creek - Hooks | 20794 Evans Primary - Thurmond Dam #6 | 4.40 | 2709 | No | Medium, High |
| 4 | 6810 A Hooks - Thurmond | 20793 Evans Primary - Thurmond Dam #5 | 3.91 | 3074 | No | Medium, High |
| 5 | 6810 A Hooks - Thurmond | 20794 Evans Primary - Thurmond Dam #6 | 3.91 | 3074 | No | Medium, High |

- The DESC center of rank 1 is Urquhart alone, because Aiken PSA has no point. 16007's
  two MEDIUM points are customer substations about a mile from the named streets.
  Rank 1 still holds: the PDF (page 43) calls 6810 O a 4.5-mile line from Urquhart to
  the Aiken PSA tap, so its true center is within 2.25 miles of Urquhart, and the pair
  stays in the 5-mile band unless 16007's points are also off by more than about half
  a mile the wrong way. Its 578-day gap is the band's smallest, so it would stay first
  in that band. In the `score` ranking it's rank 40 (score 7).
- Within a distance band, overlapping build windows and then the smaller date gap come
  first, which puts 6809 G (4.40 miles, 2709 days) above 6810 A (3.91 miles, 3074
  days).
- In this ranking, 6852 - 16007 is rank 8 and 06367 D-G - 20277 is rank 9.
