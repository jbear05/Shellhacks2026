---
name: regenerate-data
description: Re-run both PDF parsers, check the regenerated CSVs in data/processed for unexpected changes, and run the full test suite. Use after changing parsers/, dominionScript.py or parsers/common.py, after changing the pypdf version, or when asked to refresh or rebuild the project CSVs.
---

# Regenerate the parser CSVs

Run from the repo root. On macOS/Linux use `.venv/bin/python`.

## 1. Run both parsers

```bash
.venv/Scripts/python -m parsers.georgia_power
.venv/Scripts/python dominionScript.py
```

Expect exit code 0, "Wrote 208 projects" and "Wrote 44 projects". The known warnings
are:

- Georgia Power: TEAMS 19523, 20684 and 17900 have different need dates in Table 2 and
  on their detail pages.
- DESC: the yearly costs of 0139 M,N, 06367 A-C, H and 06810 F don't add up to their
  totals.

A new warning means the source or the parser changed. Find out which before going on.

## 2. If a parser stops with an error

A `ParseError` or a `ValueError` naming a page means the PDF text no longer matches
what the parser expects. Look at the extracted text of that page before loosening a
regex:

```bash
.venv/Scripts/python -c "from pypdf import PdfReader; print(PdfReader('<pdf path>').pages[<page - 1>].extract_text())"
```

The layouts are described in docs/sources/. Don't make the parser skip the problem:
it should keep failing loudly on structure changes.

## 3. Review the changes

```bash
git diff --stat data/processed/
git diff --word-diff data/processed/
```

Explain every changed row. If the changes are intended, say why in the commit message.
If the row count changed, find out which projects appeared or disappeared.

## 4. Test

```bash
.venv/Scripts/python -m pytest
```

## 5. If columns changed

- Update docs/data.md; `tests/test_docs.py` fails until it matches.
- The Georgia CSV feeds the Geolocator's `--projects-csv`, which reads `project_id`,
  `utility`, `state`, `project_name`, `project_type`, `location_1..3` and
  `voltage_1..2`. Keep those.
- Check whether the shared columns in docs/data.md still hold for both CSVs.

## 6. Commit

Commit the CSVs together with the code change that produced them, staging files by
name. Only commit when the user asks.
