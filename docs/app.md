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
