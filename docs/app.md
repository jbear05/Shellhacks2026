# App data and analysis

## Project data

`frontend/project_data.py` joins the committed parser tables to saved location
evidence by (`utility`, `project_id`). The built-in demo selects DESC and only the
Georgia Power-owned rows (GPC/SAV) from the Georgia plan. No geocoding or AI requests
are made. The original plans describe historical planning windows, not verified
current construction status.

`frontend/data_loader.py` reads CSV/XLSX identifiers as text and preserves populated
utility labels. An upload's selected utility only fills missing labels. Duplicate
keys within a utility are rejected rather than silently dropping a project; the same
ID in different utilities is valid. Numeric IDs stored in an Excel cell cannot regain
leading zeros already lost by Excel; store IDs as text in the source workbook.

The UI uses the existing title-case project columns and retains additional source
columns. Source file/pages, description, endpoint confidence, OSM IDs, reasons,
verification notes and date warnings remain available for inspection/export.

## Centers and confidence

For the saved plans, use `location_1` and `location_2` from the per-location files.
Average two complete, bounded coordinate pairs; use the sole complete point if
only one is available. Extra locations do not enter this calculation. If neither
endpoint is usable, the center stays blank. LOW points remain explicitly flagged.
Project confidence is the weakest of the named endpoints, including missing ones.

`Center Method` records which case applied: `endpoint_midpoint` (two points),
`single_location` (only one endpoint named), `one_of_two_endpoints` (two named,
but only one has usable coordinates, so the center is that endpoint rather than
the midpoint) or `unavailable`. The fallback case is always LOW, because the
missing endpoint counts as LOW. In the built-in demo on 2026-09-27, after the VCS1,
VCS2, Hooks, Coleman and Ritter overrides, there were 12 DESC and 17 Georgia Power
`one_of_two_endpoints` rows, and 4 DESC and 37 Georgia Power `single_location` rows.

The Overlaps page's map (`frontend/map_view.py`) shows where each center comes from.
A project's located substations are rings in its utility's color, joined by a thin
straight line when there are two, so a midpoint center sits in the middle of that
line. A `one_of_two_endpoints` center is drawn faint with a solid rim. Each center's
tooltip says how it was made, for example "Center: midpoint of VCS2 and Ward". The
focused pair always shows its substations, and the "Show the substations behind every
center" checkbox shows them for every project. When the focused pair's projects share
a substation, as 6810 A and 20793 share Thurmond, one ring covers the other. Which
missing endpoints could still change an overlap is in
[geolocator.md](geolocator.md#known-wrong-or-weak-lookups).

The distance circles (on by default) are shaded around each center that has a pair,
or only the focused pair's two. Their radius is half the threshold, 12.5 miles by
default, so a blue and an orange circle overlap exactly when their centers are within
the threshold. A full-threshold radius would make circles overlap up to twice the
threshold apart. The circles don't respond to clicks, so they never hide a center or a
line.

## PDF uploads

`frontend/pdf_import.py` accepts the two exact organizer PDFs, recognized by SHA-256
content rather than filename. It loads the corresponding committed deterministic
parser table and joins its rows to saved location evidence. The Georgia upload selects
GPC/SAV. Parser fixes require regenerating the committed table; uploading the same PDF
does not silently replace it with a different extraction.
Unknown/revised PDFs are rejected with instructions to import a project table;
reusing coordinates from an older plan without review would be misleading. No
generated CSV, source PDF, cache or API account is changed by an upload. The source
hash is included in the imported project table. The real-PDF adapter tests are slow.

For imports with coordinates but no endpoints, keep the supplied center and label
its method `provided_center`. After endpoint edits, recalculate the center; clearing
previously used endpoints clears the old center. A latitude from one incomplete
point is never combined with a longitude from another.

On the Location Verification page, a center typed for a center-only project is kept,
even when it had no center before, and its method becomes `provided_center`. A center
typed for a project whose center comes from its endpoints (any endpoint with a name or
a coordinate) would be recalculated away, so it is ignored with a warning, and the
project keeps its confidence and evidence. Edit its endpoints instead.

Invalid dates or reversed build windows are warnings, not silently repaired values.
Source strings remain available. A missing DESC start date keeps its documented
open-ended meaning; see [pipeline.md](pipeline.md#4-overlaps).

## Overlaps and ranking

`frontend/analysis.py` calculates haversine distance with radius 3958.8 miles, using
unrounded distances for the threshold. Only pairs from the two selected, distinct
utilities qualify. Rows marked Excluded in either review-status field are omitted.
The confidence filter can also omit LOW/unclassified locations. An empty result
retains the export schema.

The user selected distance-first ranking on 2026-09-26. The shared root `ranking.py`
orders distance bands (up to 5, 15, then 25 miles) first, followed by overlapping
build windows, smaller in-service date gaps, voltage compatibility, type
compatibility, exact distance and stable project keys. Its original equal-weight
score remains an optional mode; the 0-15 total is supplementary in distance-first
mode. A missing start is open-ended only for DESC; another utility's unknown start
does not establish an overlapping build window. Reversed dates are flagged.

`tests/test_overlaps.py` reproduces all six organizer spreadsheet distances to the
hundredth using the sheet's coordinates, then separately checks the real saved
coordinates. The two GA 20277 distances use the additional LOW Purrysburg point,
unlike the sheet. The sheet has no Hooks point, so its 6810 A and 6809 E centers are
Thurmond and Stevens Creek alone; ours are midpoints with Hooks, which makes
6809 E - 20793 4.40 miles against the sheet's 8.01 (and 6810 A - 20793 3.91 against
4.09). Other coordinate differences are under 0.21 miles. Negative
projects, exclusions, missing dates, confidence filters, a distance just above
25 miles, and the teammates' synthetic overlap fixture are also checked.
