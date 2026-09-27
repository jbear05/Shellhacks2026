# Overlap Feature Status

## Updated
- Added a rough impact estimate panel for overlap opportunities.
- Added USDA 2026 state land-value references for Georgia and South Carolina.
- Added a lightweight footprint heuristic by project type to estimate shared acres.
- The overlap page now shows the estimate for the selected opportunity.
- The estimate logic is wired into the overlap results table and the overlap page UI.
- The map flow was adjusted so the overlap page focuses on the paired projects that actually match cross-utility results.

## Left To Implement
- Keep the surrounding radius behaving like a broad glow hover effect when one radius is clicked, without making the other radii light up.
- The clicked radius should stand out, but the neighboring radii should stay visually unchanged.

## Left To Check
- Verify the rough impact estimate logic with real flagged opportunities.
- Confirm the USDA state lookup and the footprint heuristic produce sensible, non-zero values for actual project types.
- Confirm the estimate text matches the selected opportunity after clicking a map point or selecting an overlap pair.
- Confirm the estimate remains accurate after any future changes to project types or state mapping.

## Notes
- The current estimate is a rough planning estimate, not an appraisal.
- It uses state-average land value per acre and a simple project-type footprint rule.
- If better acreage or parcel data becomes available later, the estimate logic should be replaced or refined.
