# AI parser

`parsers/ai_parser/` reads the projects out of a utility's project-list PDF with Claude,
so a new PDF doesn't need a parser of its own. The two hand-written parsers stay: they're
the reference the AI parser is scored against. Why it works this way is in
[decisions.md](decisions.md#ai-parser).

## Current state

**2026-09-26:** the three regressions the
[follow-up review](ai-parser-review.md#follow-up-review-of-current-working-tree) found
are fixed. The quote check keeps the whole value, replies that were split in half
replay from the cache, and each row's `utility` comes from its sponsor. The outputs in
`data/processed/ai/` were rebuilt from the cache with the fixed code, and the
[results](#results) below describe them.

Still to do:

- **Georgia's ID pass** has never run, because the API credit ran out. The extraction
  already finds all 208 of the reference's IDs, so the pass would be a cross-check
  rather than a source of missing rows. Finishing it costs about $3 (see
  [Cost](#cost)). Run `--dry-run` first and get approval, as in the
  [ai-parse workflow](../.claude/skills/ai-parse/SKILL.md).
- **DESC's `sponsor`** is the page banner on every row; see the expected differences
  under [the eval](#scoring-it-the-eval).
- Nothing downstream reads the AI CSVs yet.

`data/ai_cache/` is committed, so anyone can rebuild the outputs without a key or any
cost. These commands check the code against the cache and write to a separate folder:

```bash
.venv/Scripts/python -m parsers.ai_parser "Sperry-Tech-Challenge/Project Listings/Dominion Energy/2024-2028-2million-and-above-project-descriptions.pdf" --utility "Dominion Energy South Carolina" --state "South Carolina" --sponsor DESC --prefix desc_recheck --out-dir data/processed/ai/recheck --offline
.venv/Scripts/python -m parsers.ai_parser "Sperry-Tech-Challenge/Project Listings/Georgia Power/2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf" --utility "Georgia Power" --state Georgia --prefix georgia_recheck --out-dir data/processed/ai/recheck --pages 171-440 --no-inventory --offline
.venv/Scripts/python -m parsers.ai_parser.evaluate data/processed/ai/recheck/desc_recheck_projects.csv data/processed/dominion_projects.csv
.venv/Scripts/python -m parsers.ai_parser.evaluate data/processed/ai/recheck/georgia_recheck_projects.csv data/processed/georgia_power_projects.csv
```

A fully scanned PDF needs OCR first. The parser reads a PDF's embedded text, and it
has no OCR and no UI upload.

## Running it

It needs an API key (`ANTHROPIC_API_KEY`, or `ant auth login`) unless every reply is
already cached. Start with `--dry-run`, which counts the requests and calls nothing.

```bash
.venv/Scripts/python -m parsers.ai_parser "Sperry-Tech-Challenge/Project Listings/Dominion Energy/2024-2028-2million-and-above-project-descriptions.pdf" --utility "Dominion Energy South Carolina" --state "South Carolina" --sponsor DESC --prefix desc_ai --dry-run
.venv/Scripts/python -m parsers.ai_parser.evaluate data/processed/ai/desc_ai_projects.csv data/processed/dominion_projects.csv
```

Drop `--dry-run` to run it. For Georgia Power use `--utility "Georgia Power" --state
Georgia --prefix georgia_power_ai`, and `--pages 171-474` to read only the Ten-Year Plan.

| Option | Use |
|---|---|
| `--pages 171-474` | Read only these pages |
| `--offline` | Use only cached replies, and fail if one is missing. For teammates without a key |
| `--workers 4` | Send 4 requests at a time. The SDK retries rate limits |
| `--effort medium` | Less thinking during extraction: cheaper, maybe less accurate. The eval tells |
| `--model claude-sonnet-5` | A cheaper model. Only worth it if it scores as well on the eval |
| `--no-inventory` | Skip the ID pass (about half the input tokens, little output) |
| `--no-fallback` | Don't let the API retry a declined request on another model |
| `--chunk-chars` | Characters of page text per request (default 12,000) |

It writes three files to `data/processed/ai/`, described in
[data.md](data.md#dataprocessedaiprefix_projectscsv):

- `<prefix>_projects.csv`: one row per project, with `status` `VERIFIED` or
  `NEEDS_REVIEW`. It has the Georgia parser CSV's location and voltage columns, so it can
  go to the Geolocator's `--projects-csv`.
- `<prefix>_review.csv`: every value that failed a check, and every disagreement.
- `<prefix>_evidence.json`: every value with the text it was copied from and its page.

## How it works

1. pypdf extracts each page's text. The model reads this text, and the checks compare
   against the same text, so a quote that isn't there was made up rather than read
   differently.
2. The pages go out in chunks of about 12,000 characters, each labelled
   `=== PAGE n ===`. Each chunk starts on the previous chunk's last page, so a project
   that runs onto the next page is whole in one of them.
3. The model returns project fragments: whatever fields one place in the PDF gives for
   a project (a table row, a detail page). Every field is a quote plus its page, and
   dates add the model's ISO reading. The API enforces the JSON schema in
   `parsers/ai_parser/schema.py`. It also labels each page as a project list, a project
   detail page, a list of excluded (cancelled or completed) projects, or other.
4. Python merges the fragments on project ID. That's how Georgia's Table 2 row and its
   detail page, 40 or more pages apart, become one row.
5. A second pass lists only project IDs, with chunk boundaries moved by half a chunk,
   as a cross-check for skipped projects.
6. Every successful reply is cached in `data/ai_cache/`, keyed on the model, prompt,
   schema, effort and page text. Unchanged requests reuse cached replies. When a reply
   is too long and the chunk is asked again in halves, the cache records the split,
   so a rerun or `--offline` goes straight to the halves' replies.
7. Each row's `utility` comes from its sponsor. For Georgia Power's plan, which also
   lists other utilities' projects, the sponsor code maps to its owner with the Georgia
   parser's own table (`parsers/utilities.py`: `GPC` and `SAV` are Georgia Power, and
   `GTC`, `MEAG` and `DU` are the other utilities). A row with no sponsor read gets a
   blank `utility`. An unknown sponsor is kept as the `utility`. Both of those go to the
   review file. For any other PDF, `utility` is `--utility`, unless the printed sponsor
   names someone else, which is kept and reviewed.

The model never works a value out. Voltages come from `extract_voltages` on the checked
title (or description), and `line_miles` and `miles_mentioned` from `extract_miles` on
both, as in the hand-written parsers. DESC's `start_date`, which `dominionScript.py`
derives from the spending table, stays blank because the PDF doesn't print one.

## The checks

| Check | Catches | Result |
|---|---|---|
| The quote is on the page it cites, ignoring case, spacing and dash style | Made-up values; a value copied from another page, which is often another project | Value left blank; row `NEEDS_REVIEW`; the reason says which page it's really on |
| A date's ISO value is one of the dates in its quote (m/d/y, YYYY-MM-DD or "Month d, yyyy") | Misread or mistyped dates | Same |
| A date with no day ("Summer 2027") | Dates that would have to be made up | Same |
| Two places give different values (the earlier page is kept, as the Georgia parser keeps Table 2) | Contradictions in the source, such as TEAMS 19523's need dates | `NEEDS_REVIEW` |
| The ID pass and the extraction disagree | Skipped projects | A review row, and `NEEDS_REVIEW` for a project the ID pass missed |
| A page labelled as a project page gave no project | Skipped pages | A review row |
| No name or in-service date; a year outside 1990-2060; a start after the in-service date; over 300 miles | Values that look wrong | `NEEDS_REVIEW` |
| The reply was cut off, declined, or isn't in the schema | Structural failures | Cut-off chunks are asked again in halves; otherwise the run stops and writes nothing |

Ignoring spacing matters for Georgia's Table 2, where pypdf splits `PRI-ECHECONNEE`
over two lines. The value written is always the page's own text, spelling and case,
whitespace collapsed and dashes as hyphens, even when the model's quote differs from it
in case or spacing. So a title split after a hyphen keeps the space
(`PRI- ECHECONNEE`), exactly as the Georgia parser writes it. The quote has to match
whole words, so `9523` doesn't pass inside `19523`, nor `Cre` inside `Creek`.

**What the checks can't catch:** a quote proves the value is on the page, not that it's
in the right field. On Georgia's detail pages pypdf prints every label before every
value, so a swapped Need Date and Start Date would pass the quote check. The order
check catches a swap only when the start then falls after the need date. The eval
catches the rest, which is why it matters.

An earlier check against the real PDFs found that every project ID, name and description
the hand-written parsers extracted (964 values) passed the quote check on its page.
That check didn't test that the whole value is kept. The replays in [Results](#results)
do: every ID, name and description matches the reference.

## Scoring it: the eval

`python -m parsers.ai_parser.evaluate AI_CSV REFERENCE_CSV [--differences out.csv]`
matches rows on (`utility`, `project_id`), the join key everything downstream uses, so
a row with the wrong or a blank `utility` counts as missing and extra. For each column
it counts the values that are the same, differ, are blank in the AI CSV only, or are
in the AI CSV only. The `VERIFIED` summary counts matched rows that differ in
`project_name`, `in_service_date` or `start_date` (a blank AI `start_date` excepted),
and `VERIFIED` rows that match nothing in the reference. Read the missing and extra
counts and every column too: the summary alone doesn't show that the output is right.

Differences to expect even when the AI parser is right:

- DESC `start_date`: derived by `dominionScript.py`, blank here.
- DESC `sponsor`: the model copies `Dominion Energy South Carolina` from the header on
  every page, where `dominionScript.py` writes the code `DESC`. The quote is on the page,
  so the check can't catch it. `utility` is still right, and nothing downstream reads
  `sponsor`. A prompt change would fix it but changes every cache key, so it would have
  to wait for a paid run.
- DESC locations: they aren't in `dominion_projects.csv`, but the Geolocator's
  hand-typed list has them. The model copies names as printed (`Ladson Jct`,
  `LR Plumb Branch`) where the list spells them out (`Ladson Junction`,
  `Plumb Branch`).
- Georgia locations: the reference's are guesses from the title, while the model also
  takes places from the description, so it usually lists more. TEAMS 18670 adds
  `McClure Industrial` and `Ridgeway Church Road` to `BANKS CROSSING` and `POND FORK`.
  A title abbreviation and its spelled-out form can both appear (`BONAIRE PRI`,
  `BONAIRE PRIMARY`).
- TEAMS 21046's title has `23O KV` (a letter O). The Georgia parser corrects it and
  takes 230 kV from the title; the AI parser finds no voltage there and takes 230 and
  115 kV from the description.
- `NEEDS_REVIEW`, correctly: TEAMS 19523, 20684 and 17900 (Table 2 and the detail page
  give different need dates), 18832, 20781, 21076 and 21053 (they give different
  titles; see [the Georgia PDF's inconsistencies](sources/georgia-power-pdf.md#inconsistencies-in-the-source)),
  and 20248 (starts after its need date).
- Page 302 is reported as a project page nothing was read from. It's the overflow page
  of TEAMS 09662's detail page, and holds only redacted cost labels.

## Results

The first runs, 2026-09-26, `claude-opus-5` at effort `high`, rebuilt from the cache
with the current code the same day. Projects count as found only when both `utility`
and `project_id` match the reference.

| Run | Projects found | Compared values that differ | `VERIFIED` rows that are wrong |
|---|---|---|---|
| DESC, all 44 pages | 44 of 44, none extra | None, apart from the expected `sponsor` and `start_date` | 0 of 44 |
| Georgia, pages 171-440, no ID pass | 208 of 208, none extra (138 Georgia Power, 54 GTC, 14 MEAG, 2 DU) | None in name, sponsor, dates, mileage, voltage_1 or description; voltage_2 only for 21046 | 0 of 200 |

The rebuild changed only what the fixes should have changed. The DESC CSV is
byte-for-byte the same. In the Georgia CSV, 70 rows gained their real owner's
`utility`, 2 sponsors went from the model's `du` to the page's `DU`, and 4 titles
split after a hyphen now keep the page's space, as the Georgia parser does.

Georgia's cancelled and completed projects (Tables 3 and 4) were left out, as they
should be. Compared with the Geolocator's hand-typed DESC list, 36 of the 44 projects
have exactly the same locations.

The Georgia run stopped at page 440 when the account's credit ran out, before the ID
pass. Every project is on pages 177-425, so the output
(`data/processed/ai/georgia_power_ai_partial_projects.csv`) is complete apart from the
ID pass's cross-check. It was rebuilt from the cache with `--pages 171-440
--no-inventory --offline`. Running the full command again sends only the missing
requests.

Keep the prompt free of rules for one particular PDF, and don't show the model the
reference CSVs, so the score says something about a PDF it hasn't seen.

## Cost

Measured on the first runs, on `claude-opus-5` ($5 per million input tokens, $25 per
million output):

| Run | Requests | Input tokens | Output tokens | Cost |
|---|---|---|---|---|
| DESC, extraction | 3 | 23,546 | 12,006 | $0.42 |
| DESC, ID pass | 4 | 19,218 | 729 | $0.11 |
| Georgia pages 177 and 231-233 (a test) | 3 | 11,374 | 3,629 | $0.15 |
| Georgia pages 171-440, extraction | 45 | 339,007 | 119,611 | $4.69 |

Output tokens include the model's thinking. Every request also carries about 4,800
input tokens of prompt and schema (2,600 for the ID pass), so for Georgia that overhead
was more than half the input. Larger chunks (`--chunk-chars 24000`) would cut the
input by about a third, but haven't been tried and change every cache key.

`--dry-run` counts each request as 1,270 tokens plus one per 1.75 characters of page
text (650 plus one per 2 characters for the ID pass), in `INPUT_TOKENS` in
`parsers/ai_parser/__main__.py`. On the cached DESC and Georgia requests that's within
4% of the input tokens actually billed.

To finish Georgia pages 171-474, `--dry-run` estimates about 69,500 input tokens for
the last 10 extraction requests (pages 440-474, which hold no projects) and 336,000 for
the ID pass: about $3 in all with output, or $0.75 with `--no-inventory`. All 668
pages would cost about twice as much as 171-474. The log gives each run's tokens and cost, from the
prices in `parsers/ai_parser/llm.py`.

## Tests

`tests/test_ai_parser.py` never calls the API. The model's replies are written by hand
over page text copied from pypdf's output of the real PDFs.
`tests/test_ai_parser_cache.py` checks that split replies replay online and offline
without a request, and that `--dry-run` counts them. Two tests marked `slow`
send a request through the real SDK to a mock HTTP transport, which checks the request
the API would get (streaming, JSON schema, effort, fallback) and the reply parsing.
