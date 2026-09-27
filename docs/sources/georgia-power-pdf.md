# Georgia Power PDF

`Sperry-Tech-Challenge/Project Listings/Georgia Power/2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf`:
668 pages of real text (no OCR needed). This is the redacted public version the
organizers supplied. `parsers/georgia_power.py` is built on the findings below, and
`tests/test_georgia_power_pdf.py` checks them against the real file.

## Finding the plan

Use the bookmarks. "2 - 2024 GA ITS Ten Year Plan" covers PDF pages 171-474. A PDF
page number is the plan's own page number plus 170.

## Table 2, the project list (PDF 177-190)

- Columns: Zone, Year, TEAMS #, Project Name, Need Date, Sponsor, then costs, which
  are all `REDACTED`.
- Names wrap over 2 or 3 lines, so a row is matched from its zone/year/TEAMS start to
  its date/sponsor/REDACTED end, not line by line.
- The table ends at a `Total REDACTED ...` row. Tables 3 (Cancelled) and 4 (Completed)
  follow on PDF 191-192 and must be left out.

## Section IV detail pages (PDF 214-425)

- One per project, found by its `Teams # NNNNN` header, with Need Date and Start Date
  on the next line.
- pypdf prints all the form labels first and their values afterwards, so values are
  read by position once the fixed form text is removed. What remains is always:
  description, `REDACTED` (the supporting statement), change vs previous plan, change
  vs previous IRP.
- East Walton (TEAMS 09662) spills onto a second page. Cutting the text into one chunk
  per project first is what stops it swallowing the next project.
- PDF 426-474 are extracted but unused; skipping them would save about 1.5 s.

## Boilerplate

Every page repeats a CEII banner, a "Page N of 304" footer, "PUBLIC DISCLOSURE" and
the table header. The parser strips all of them.

## Titles

`location_*`, `project_type` and the voltages are guessed from the Table 2 title. The
title fixes in the parser cover typos and abbreviations seen in this plan (`23O KV`,
`V. RICA`, `PRI`, `RD`, `TALLBOT`). A sponsor or program prefix (`SAV:`, `GTC:`,
`CC -`, `GRID -`) is removed first. Bracketed owner names become `owner_tags`.

## Counts

208 projects by sponsor: GPC 122, GTC 54, SAV 16, MEAG 14, DU 2. Georgia Power
itself is GPC plus SAV (the Savannah area, formerly Savannah Electric). Every cost is
redacted.

## Inconsistencies in the source

- TEAMS 19523, 20684 and 17900 have different need dates in Table 2 and on their
  detail pages. The parser uses Table 2 and logs a warning.
- TEAMS 20248 (Bay Creek - Conyers) starts on 2031-06-01 but is due on 2029-12-31 in
  both places. No warning is logged for it yet.
- Four titles differ between Table 2 and the detail page. The parser uses Table 2's
  and doesn't compare them; the AI parser found these
  ([ai-parser.md](../ai-parser.md#results)):
  - 18832: `MEAG: FORTSON 230KV SUBSTATION MODERNIZATION`, and on PDF 223 without
    `230KV`.
  - 20781: `(CC IMPROVMNT)`, and `(CC IMPROVEMENT)` on PDF 294.
  - 21076: `GTC: TALLBOT #2 - TAZEWELL 500KV LINE`, and `TALBOT` on PDF 389.
  - 21053: `MCEVER ROAD - SHOAL CREEK 115KV REBUILD PHASE III`, and without
    `PHASE III` on PDF 417.
