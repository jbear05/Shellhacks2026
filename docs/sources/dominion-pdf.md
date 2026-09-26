# DESC PDF

`Sperry-Tech-Challenge/Project Listings/Dominion Energy/2024-2028-2million-and-above-project-descriptions.pdf`:
44 pages, one project per page, exported from Word, real text. `dominionScript.py` is
built on the findings below, and `tests/test_dominion_script.py` checks them against
the real file (in under a second).

## Page layout

- **Title:** between `5 Year Budget` and `Project ID`.
- **Labels,** each on its own line: `Project ID`, `Project Description`,
  `Project Need`, `Project Status`, `Planned In-Service Date`,
  `Estimated Project Cost`. The parser splits the page on them.
- **Dates:** a mix of `12/31/23` and `12/31/2024`. Page 34 has
  `10/1/2025 (phase 1) and 10/1/2026 (phase 2)`, so the parser finds every date in the
  field and keeps the last one.
- **Dashes:** names and descriptions mix en-dashes and hyphens. `normalize_text` turns
  them all into hyphens.
- **Mileage:** 19 projects give one, either in the description (page 14, "9.5 miles")
  or in the title (page 20, "Approx 18 Miles"). The cost estimate needs it.

## Cost table

- The header is `Previous 2024 2025 2026 2027 2028 Total*`, but the asterisk is
  missing on pages 14, 15 and 25.
- The cells wrap unpredictably, so the parser takes the `$` amounts in order. There
  are always exactly 7: previous, 2024 to 2028, and the total.
- The years with spending give the build window. 29 of the 44 projects have spending
  under "Previous", so their start is some time before 2024.
- Three totals don't add up. The parser logs a warning and keeps the values as
  printed:
  - 0139 M,N: the years come to $587,000 less than the total.
  - 06367 A-C, H: a typo, `$19,00,181` for $19,000,181.
  - 06810 F: due 12/31/29, so the total includes spending after 2028.

## Project IDs

The PDF writes `06367 A - C, H` and `06367 D - G`, while the Geolocator's list has
`06367 A-C, H` and `06367 D-G`. The other 42 IDs match exactly. A plain join would have
dropped these two (Riverport Tap and Jasper - Okatie #2), which are next to Savannah.

The parser removes the spaces around `-`, but not around `,`, which the Geolocator keeps
in `1060A, I, L`. All 44 IDs now match the list exactly. Titles differ in spacing too
(`Yemassee- Ritter` in the PDF, `Yemassee-Ritter` in the list), so always join on ID.

## Locations

The PDF has no location fields. The Geolocator's `PROJECTS` list names the locations
for all 44 projects by hand, so the parser doesn't derive them; see
[pipeline.md](../pipeline.md#1-parse).

## History

A teammate's first version of `dominionScript.py` imported `PyPDF2`, opened the PDF by
bare filename and printed three fields (ID, title, in-service date). It was reworked in
place, keeping its regexes. Compared with that version's output, the three original
fields only changed in the two IDs above, 6859's date (the later phase), ISO dates, and
hyphens for en-dashes.
