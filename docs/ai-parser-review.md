# AI parser review notes (2026-09-26)

The [follow-up review](#follow-up-review-of-current-working-tree) below describes the
current working tree. The earlier notes are retained as history; several of their
open items have since been changed in code.

Findings from a read-only review session that watched the `feat/ai-parser` work while
another session wrote it. Nothing here was changed by the reviewing session. Line
numbers are as of the end of the session (the branch had no commits yet).

Everything under "Open" was either reproduced by running code or read directly from
the source; each item says which.

## Open

### 1. DESC sponsor is the page banner, on every row (medium)

In the first real run (DESC, all 44 pages), the model copied the banner "Dominion
Energy South Carolina" (page 1 onward) as every project's `sponsor`. The quote is on
the page, so it passes the check and all 44 rows are `VERIFIED`. The run passed
`--sponsor DESC`, but that default only applies when no sponsor was read, so it never
applied. Every row differs from `dominion_projects.csv` (`DESC`).

The eval hides it: its last line reports 0 wrong `VERIFIED` rows because `sponsor` isn't
in `KEY_COLUMNS` (`parsers/ai_parser/evaluate.py:27`). The prompt already says to take a
sponsor "only when it's printed for this project" and warns that banners repeat, so
this is the "right text, wrong field" gap that `docs/ai-parser.md` admits to.

Options: tighten the prompt, add `sponsor` to `KEY_COLUMNS`, or list it under
"differences to expect" in `docs/ai-parser.md`. Checked by running the eval and reading
`data/processed/ai/desc_ai_evidence.json`.

### 2. `--dry-run` underestimates input tokens about 2.5x (medium, it's money)

`CHARS_PER_TOKEN = 3.5` (`parsers/ai_parser/__main__.py:23`) is too high for this text,
and the estimate leaves out the system prompt and JSON schema sent with every request.
Measured from the 7 cached DESC replies:

| Pass | Page text, estimated at 3.5 chars/token | Actual input tokens |
|---|---|---|
| Extraction (3 requests) | about 9,400 | 23,546 |
| ID pass (4 requests) | about 9,600 | 19,218 |

A linear fit gives about 2.1-2.2 characters per token, plus about 2,900 tokens of fixed
overhead per extraction request and about 700 per ID-pass request. The `/ai-parse`
skill tells agents to quote the dry-run estimate when asking to spend money, so users
are shown a low number. For Georgia (106 + 107 requests) the same rates give about
1.4M input tokens, roughly $7 of input alone, which puts the "$8-12" estimate in
`docs/ai-parser.md` at or above its top end once output is added. Better: count tokens
with the API's token counting endpoint, or use the measured rate plus the overhead.

### 3. The `/ai-parse` skill refuses a valid `ant auth login` (low-medium)

`.claude/skills/ai-parse/SKILL.md:12-19` only tests `$ANTHROPIC_API_KEY` and says to stop
if it's unset. `docs/ai-parser.md:10` says `ant auth login` works too, and the SDK reads
that profile with no environment variable. `ant auth status` would detect both. Read
from the source.

### 4. The quote check sometimes keeps the model's spelling, not the page's (low)

`PageText.find` (`parsers/ai_parser/checks.py:51`) first looks for the quote ignoring
case and dash style, and returns the page's own text. When that fails and the
no-spaces fallback matches (line 61), it returns the model's text instead, including
its capitals. Reproduced: with the page text `GTC: BONAIRE PRI-\nECHECONNEE 115 KV`, the
quote `gtc: bonaire pri-echeconnee 115 kv` passes and the kept value is the lowercase
quote. `docs/ai-parser.md:80` says the value written is always the page's own spelling.
The eval ignores case, so scores aren't affected, but the CSV can hold text the PDF
doesn't print. Fix the code (map the match back to the page's characters) or the doc.

### 5. Short quotes match inside longer words (low, design)

The same check is a plain substring search with no word boundaries, so a short value
(a sponsor code, a numeric ID, a place name like "Lee") passes if it appears anywhere
on the cited page, including inside another word or number ("Leesville"). A made-up
short value can pass. Read from the source.

### 6. The first page can be sent to the model twice (low, cost only)

When pages 1 and 2 together exceed `--chunk-chars`, `make_chunks`
(`parsers/ai_parser/pages.py:40`) makes a chunk of page 1 alone and then a chunk of
pages 1-2, so the first request is wasted. The duplicate review rows it used to cause
were fixed (see below), but the extra request remains. Two tests depend on it:
`test_a_page_over_the_budget_still_gets_a_chunk_with_its_neighbour` (line 199) expects
`[[1], [1, 2], [2, 3]]`, and `test_a_page_read_by_two_chunks_gives_each_problem_once`
(line 293) uses it to read page 177 twice, so both need updating if it's fixed.

### 7. The fallback model isn't visible in the outputs (low, traceability)

Only each cache entry records which model answered. The evidence JSON's `model` is
`args.model` (`parsers/ai_parser/__main__.py:82`), and `Model.cost()` prices every
request at the requested model's rates. If the server-side fallback answers a chunk,
neither says so. It didn't happen in the DESC run. Read from the source.

### 8. Smaller items

- A run stopped between writing `data/ai_cache/<key>.json.tmp` and renaming it
  (`parsers/ai_parser/llm.py:125-127`) leaves the `.tmp` file, which isn't git-ignored
  (checked with `git check-ignore`), so `git add data/ai_cache` would commit it. The
  Geolocator's `gridlock_geocode_cache.json.tmp` is ignored.
- `evaluate --differences` doesn't catch `OSError` on its write
  (`parsers/ai_parser/evaluate.py:150`), so a missing `data/processed/ai/` gives a
  traceback. The command is pre-approved in `.claude/settings.json` and can overwrite
  any path it's given, and the `Edit(Sperry-Tech-Challenge/**)` deny rule doesn't cover
  files written by shell commands.
- `docs/data.md:115` and `docs/pipeline.md:45` say the AI CSV uses the Georgia parser
  CSV's column names. It shares only the first 14, adds `pages` and `status`, and lacks
  `plan_year`, `zone` and the rest. `docs/ai-parser.md:36` says it more accurately.
- `.env.*` in `.gitignore` also ignores `.env.example`, if one is ever wanted. Add
  `!.env.example` then.

## Fixed during the session

| Found | Fix |
|---|---|
| `assert rows[...]["voltage_1"], rows[...]["voltage_2"] == (...)` only checked that `voltage_1` wasn't blank; the comparison was the assert message | Now compares the tuple |
| The "start after in-service" test never produced that case | Replaced by `test_swapped_dates_pass_the_quote_check_but_not_the_order_check` |
| `anthropic` and `pydantic` weren't in `requirements.txt`, so the fast suite failed to import for a fresh install, and the cache keys depended on an unpinned pydantic | Both pinned (1.8.0, 2.13.5) |
| `docs/ai-parser.md` was linked but didn't exist | Written |
| `--pages 171-474,500` was recorded as `171-500` in the evidence JSON | Records the spec as typed |
| The `slow` marker's description in AGENTS.md didn't cover the SDK tests | Updated |
| A page read by two chunks gave each problem twice in the review file | `Project.add` drops exact repeats |

## First real run: DESC, all pages

| | |
|---|---|
| Projects | 44 in both CSVs, none missing, none extra |
| Same as `dominion_projects.csv` | `project_name`, `in_service_date`, `description`, `line_miles`, `miles_mentioned`: 44 of 44 |
| `start_date` | 29 same (both blank), 15 blank in the AI CSV, as expected |
| `sponsor` | 44 differ (finding 1) |
| Status | 44 `VERIFIED`, empty review file |
| Quotes | All 119 in the first reply re-checked on their pages; all pass |
| Requests | 3 extraction + 4 ID pass, all answered by `claude-opus-5` (no fallback) |
| Tokens | 42,764 input, 12,735 output, about $0.53 at $5/$25 per million |

The full suite passed at the end of the session: 132 tests, 125 of them fast.

## Follow-up review of current working tree

Reviewed `feat/ai-parser` on 2026-09-26. At review time HEAD was `1c49c6e`, also local
`main`, and the AI parser implementation and related changes were uncommitted. The
review changed only documentation. It made no paid API calls and did not rewrite saved
CSVs or caches. The subsequent handoff snapshot includes those files with these
findings unresolved; the full suite was rerun before publication with the same results.

### Findings

1. **P1: quote matching truncates correct values and merges distinct IDs.** In
   `PageText.find` (`parsers/ai_parser/checks.py:64-66`), the `spans` generator reads
   `len(needle)` after `needle` has been reassigned to the version without spaces.
   Its start positions use the original quote but its end positions use the shorter
   length. `PageText([Page(1, "6809 E")]).find("6809 E", 1)` returns `"6809 "`, which
   becomes ID `6809`. Freeze the original match length or materialize its spans
   before reassigning the variable. The whole-word check does not prevent truncation
   at whitespace or punctuation. Both extraction and inventory use the same faulty
   check, so the inventory cannot reliably detect the damage.
2. **P2: successfully split responses cannot be rebuilt offline.** `_ask_chunk`
   (`parsers/ai_parser/pipeline.py:112-121`) splits only on `AnswerTooLong`. After a
   long reply has been replaced by cached child replies, the original request has
   no cache entry. The next `--offline` run raises `ModelError` for that parent and
   never visits its cached children. A mock two-page run reproduced this: three
   requests, two cached children, successful first run, then offline failure for
   pages 1-2. Persist the split decision or resolve cached child requests on replay;
   otherwise an online rerun pays for the same oversized parent again too.
3. **P2: mixed-utility PDFs lose their per-project utility identity.** `to_row`
   (`parsers/ai_parser/records.py:253`) writes `--utility` to every row. Compared by ID
   with the hand-written reference, the saved Georgia CSV labels 70 other-utility
   projects as Georgia Power: 54 Georgia Transmission Corporation, 14 MEAG Power and
   2 Dalton Utilities. The evaluator excludes this column, and the Geolocator reads
   it unchanged, so this breaks the prescribed `(utility, project_id)` joins and can
   include the wrong owners in overlap results. This is a documented design choice
   in the current parser, but still an integration gap to resolve before using its
   CSV downstream. Preserve owner identity through a checked mapping or explicitly
   filter the requested utility's sponsors.

### Verification

| Check | Observed result |
|---|---|
| Fast suite | 119 passed, 7 failed, 7 deselected |
| Full suite | 125 passed, 8 failed |
| Saved DESC CSV | 44 IDs match the reference; names, in-service dates and descriptions match |
| Saved Georgia partial CSV | 208 IDs match the reference; names, start dates, in-service dates and descriptions match |
| Current DESC replay, cached replies only | 28 rows instead of 44; only 5 IDs match the reference; 24 rows still marked `VERIFIED` |
| Current Georgia replay, pages 171-440, no inventory, cached replies only | 208 rows; 54 names and 75 descriptions differ; 52 of the 200 `VERIFIED` rows have wrong names |

The offline replays used `read_pages`, `run`, and `Model(..., offline=True)` in memory;
both reported zero API requests. They did not overwrite the earlier successful outputs.
The full CLI's output writes were covered by the existing tests, not a fresh paid run.

Five failing tests exercise the quote-truncation bug. Three other assertions lag
behind recent changes: the oversized-page test still expects a redundant first
chunk; the split-word test expects the model's spacing rather than the page's;
and the mock SDK test indexes `model.usage["output_tokens"]` even though usage is
now nested by answering model. Update these expectations to the intended behavior
and use `model.tokens("output_tokens")` for the aggregate. The duplicate-chunk test's
two-page fixture also no longer creates overlapping chunks, so its passing result
does not exercise its stated purpose.

The sandbox could not launch the venv's Windows Store Python or use pytest's existing
temporary directory. The reported suite results come from running the repository's
venv commands outside the sandbox. Read-only reproductions used bundled Python
3.12.14 with the repository venv's installed packages.
