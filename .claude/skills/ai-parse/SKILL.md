---
name: ai-parse
description: Run the AI parser (parsers/ai_parser) on a project-list PDF, score it against a hand-written parser with the eval, and summarize what needs review. Use when asked to parse a PDF with AI or Claude, run or re-run the AI parser, evaluate or score it, or tune its prompt.
---

# Run the AI parser

The AI parser calls the paid Claude API. Read docs/ai-parser.md first, especially
its current state. After changing the parser's Python, rebuild the saved outputs from
the cache with `--offline` and score them before paying for anything new.

## 1. Check the key and agree on the cost

Check that `ANTHROPIC_API_KEY` is set without printing it:

```bash
if [ -n "$ANTHROPIC_API_KEY" ]; then echo set; else echo "not set"; fi
```

If it isn't set, `ant auth status` (if the `ant` CLI is installed) may show a login,
which the SDK uses too. On Windows, a key saved with `setx` reaches only programs
started afterwards; `[Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY", "User")`
in PowerShell reads it without restarting. If there's no key at all, stop and point the
user to docs/ai-parser.md. Never ask for the key in chat, never print it, and never
write it to a file.

Then run the same command with `--dry-run`, and give the user the request counts and
the input-token estimate it prints, plus the output cost from docs/ai-parser.md#cost
(about $1 for DESC; about $3 to finish Georgia Power pages 171-474). Wait for their
go-ahead. Cached replies cost nothing, and `--offline` never
calls the API.

## 2. Run it from the repo root, in the background

```bash
.venv/Scripts/python -m parsers.ai_parser "Sperry-Tech-Challenge/Project Listings/Dominion Energy/2024-2028-2million-and-above-project-descriptions.pdf" --utility "Dominion Energy South Carolina" --state "South Carolina" --sponsor DESC --prefix desc_ai
.venv/Scripts/python -m parsers.ai_parser "Sperry-Tech-Challenge/Project Listings/Georgia Power/2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf" --utility "Georgia Power" --state Georgia --prefix georgia_power_ai --pages 171-474 --workers 4
```

For a first test of a change, use a few pages (`--pages 177-178,231`). If a request
fails, run the same command again: replies that arrived are cached, and only the
missing ones are sent. The log ends with the tokens used and an estimated cost; tell
the user.

## 3. Score it

```bash
.venv/Scripts/python -m parsers.ai_parser.evaluate data/processed/ai/desc_ai_projects.csv data/processed/dominion_projects.csv --differences data/processed/ai/desc_ai_differences.csv
.venv/Scripts/python -m parsers.ai_parser.evaluate data/processed/ai/georgia_power_ai_projects.csv data/processed/georgia_power_projects.csv --differences data/processed/ai/georgia_power_ai_differences.csv
```

Rows match on (`utility`, `project_id`), so a wrong or blank `utility` shows up as
missing and extra. Read those counts and every column's scores as well as the
`VERIFIED` summary, which covers only matched rows and three columns.
docs/ai-parser.md lists the differences to expect.

## 4. Summarize for the user

- Projects found against the reference: missing, and only in the AI CSV.
- `VERIFIED` and `NEEDS_REVIEW` counts, and the `VERIFIED` rows that are wrong.
- The review file's reasons, grouped: quotes not on their page, date mismatches,
  conflicts in the source, projects the ID pass disagrees about.
- Tokens used and the estimated cost.

## 5. Improve the prompt, not the output

Change `EXTRACT_PROMPT` or `INVENTORY_PROMPT` in `parsers/ai_parser/llm.py` so the
model makes fewer of the mistakes it made. Keep the prompt general: no rules for one
PDF, and never show it the reference CSVs, or the eval stops predicting how it does on
a new PDF. A changed prompt changes every cache key, so the next run pays in full; try
it on a few pages first.

Don't hand-edit the output CSVs. Ask the user before committing the outputs or the
cache in `data/ai_cache/`, and record the eval's numbers in docs/ai-parser.md and
docs/status.md (the handoff workflow).
