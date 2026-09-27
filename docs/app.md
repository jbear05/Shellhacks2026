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

For imports with coordinates but no endpoints, keep the supplied center and label
its method `provided_center`. After endpoint edits, recalculate the center; clearing
previously used endpoints clears the old center. A latitude from one incomplete
point is never combined with a longitude from another.

Invalid dates or reversed build windows are warnings, not silently repaired values.
Source strings remain available. A missing DESC start date keeps its documented
open-ended meaning; see [pipeline.md](pipeline.md#4-overlaps-planned).

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
unlike the sheet. Other coordinate differences are under 0.21 miles. Negative
projects, exclusions, missing dates, confidence filters, a distance just above
25 miles, and the teammates' synthetic overlap fixture are also checked.
