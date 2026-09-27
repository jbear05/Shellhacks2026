# The challenge

Sperry Tech "Gridlock", ShellHacks 2026 (the weekend of 2026-09-26). This is a summary
of `Sperry-Tech-Challenge/ShellHacks_Challenge_Gridlock.docx` and
`Finding_Real_Locations_Guide.docx`.

## Goal

Build a tool that reads at least two utilities' public construction plans and flags
where their planned transmission projects overlap:

- **Geographic overlap (the primary signal):** two projects within 25 miles of each
  other.
- **Timeline overlap (a strong secondary signal):** projects scheduled in the same build
  window.

The example pair is Dominion Energy South Carolina (DESC) and Georgia Power, which
share the Savannah River border. The brief warns that most projects will *not*
overlap: finding the real matches is the point. Data marked CEII (Critical Energy
Infrastructure Information) is off-limits, so use public filings only.

## Deliverables

- Required: an interactive UI showing both utilities' projects and highlighting the
  overlaps. It has to be interactive (a map you can pan, zoom and click, not a static
  image). Any tech stack is allowed.
- Required: a ranked list of the top coordination opportunities.
- Bonus: a rough cost or impact estimate for at least one flagged opportunity, such as
  the land two projects could share or the money that would save.

## The organizers' method

From `Finding_Real_Locations_Guide.docx`:

1. **Get coordinates.** Match each project's names to OpenStreetMap features: Overpass
   for `power=substation` or `power=line` by operator, Nominatim for place names, and
   Open Infrastructure Map for a visual check.
2. **Confirm each match** against the PDF's description, zone and nearby landmarks. The
   common false match is a similarly named substation in the wrong county. Flag the
   matches you can't confirm as lower confidence.
3. **Build the overlap table.** A project's center is the midpoint of its two named
   points, or the one point that was located. Take the haversine distance between the
   centers of each DESC and Georgia Power project. Each pair under 25 miles is one row,
   with the gap in days between the two in-service dates.

## Files from the organizers

All in `Sperry-Tech-Challenge/`, and read-only.

| File | What |
|---|---|
| `ShellHacks_Challenge_Gridlock.docx` | The brief, with a glossary (IRP, SERTP, SCRTP, CEII, FERC Order No. 1920) |
| `Finding_Real_Locations_Guide.docx` | The method above, with an Overpass query |
| `Projects_Overlaps.xlsx` | The target tables with example rows; see below |
| `Project Listings/Dominion Energy/2024-2028-2million-and-above-project-descriptions.pdf` | DESC's projects; see [sources/dominion-pdf.md](sources/dominion-pdf.md) |
| `Project Listings/Georgia Power/2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf` | Georgia Power's IRP, which contains the Ten-Year Plan; see [sources/georgia-power-pdf.md](sources/georgia-power-pdf.md) |
| `Opportunities/Software_Engineer_Intern_Listing.docx` | A job listing from the sponsor; not part of the challenge |

## Target tables (`Projects_Overlaps.xlsx`)

The `projects` sheet has one row per project:

`project_id, utility, state, project_name, name_a, lat_a, lon_a, name_b, lat_b, lon_b,
lat_center, lon_center, in_service_date, overlap_count, overlap_1, overlap_2, overlap_3`

`lat_center` and `lon_center` are formulas: the midpoint, or whichever point is
present. The sheet's `project_id` is a made-up key (`DESC_1`, `GPC_1`) and `state` is
`SC` or `GA`. Our CSVs use the source IDs and full state names instead.

The `overlaps` sheet has one row per pair:

`overlap_id, distance_mi, time_gap (day), utility_a, project_id_a, project_name_a,
utility_b, project_id_b, project_name_b`

## The organizers' example answers

The sheet has 10 example projects and 6 overlaps. Use them to sanity-check the
Geolocator and the overlap code, not as ground truth: the sheet was made by hand, and
some of its cells are shifted or missing.

Its projects, mapped to ours:

| Sheet | Ours | In service |
|---|---|---|
| DESC_1 | DESC 6809 E, Stevens Creek - Hooks 115kV/LR Plumb Branch 46kV Rebuilds | 2024-12-31 |
| DESC_2 | DESC 6810 A, Hooks - Thurmond 115kV Tie | 2024-12-31 |
| DESC_3 | DESC 06367 D-G, Jasper - Okatie 230 kV #2 | 2025-12-31 |
| DESC_4 | DESC 6807 B, Queensboro - Ft Johnson | 2023-12-31 |
| DESC_5 | DESC 6808 S, Okatie-Bluffton 115kV | 2025-06-01 |
| GPC_1 | GA 20793, Evans Primary - Thurmond Dam #5 | 2033-06-01 |
| GPC_2 | GA 20277, McIntosh - Purrysburg 230kV reactors | 2026-06-01 |
| GPC_3 | GA 20065, Goshen - McIntosh 115kV rebuild | 2027-06-01 |
| GPC_4 | GA 18492, Mitchell - North Tifton 230kV reconductor | 2025-05-01 |
| GPC_5 | GA 11821, Jesup - Ludowici Primary 115kV rebuild | 2025-06-01 |

Its overlaps. Every `distance_mi` equals the haversine distance between the sheet's two
centers, with an Earth radius of 3958.8 miles, to the hundredth. `time_gap` is the
absolute number of days between the in-service dates.

| Sheet | DESC | Georgia Power | Miles | Days |
|---|---|---|---|---|
| OVL_1 | 6810 A | 20793 | 4.09 | 3074 |
| OVL_2 | 06367 D-G | 20277 | 5.65 | 152 |
| OVL_3 | 06367 D-G | 20065 | 7.55 | 517 |
| OVL_4 | 6809 E | 20793 | 8.01 | 3074 |
| OVL_5 | 6808 S | 20277 | 14.34 | 365 |
| OVL_6 | 6808 S | 20065 | 14.81 | 730 |

DESC 6807 B and GA 18492 and 11821 have no overlaps: they're useful negative cases.

The points the sheet gives in full:

| Point | Lat, lon | Projects |
|---|---|---|
| Stevens Creek Sub | 33.56260, -82.05136 | 6809 E |
| Thurmond Dam | 33.66013, -82.19593 | 20793; also DESC_2's unnamed second point (6810 A) |
| Evans Primary | 33.54399, -82.16865 | 20793 |
| Jasper Sub | 32.35912, -81.12460 | 06367 D-G |
| Okatie Sub | 32.33376, -81.03249 | 06367 D-G, 6808 S |
| Bluffton Sub | 32.23503, -80.85338 | 6808 S |
| Queensboro Sub | 32.72279, -79.96733 | 6807 B |
| McIntosh | 32.35212, -81.17511 in GPC_2; 32.35212, -81.18211 in GPC_3 | 20277, 20065 |
| Goshen | 32.24870, -81.20947 | 20065 |
| Mitchell Substation | 31.44712, -84.13384 | 18492 |
| North Tifton Substation | 31.47809, -83.54913 | 18492 |
| Jesup | 31.60311, -81.92495 | 11821 |
| Ludowici Primary | 31.72160, -81.74370 | 11821 |

Missing or broken in the sheet: Hooks Sub (no coordinates in DESC_1, and a latitude of
`27` with no longitude in DESC_2), Ft Johnson Sub and Purrysburg (no coordinates). In
those rows the center cell holds the one point that is present. We found Hooks, so our
OVL_1 and OVL_4 distances differ; see [app.md](app.md#overlaps-and-ranking).
