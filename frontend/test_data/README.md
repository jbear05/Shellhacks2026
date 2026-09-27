# Test Data

These CSV files are synthetic records for testing the Utility Intelligence workflow.

- `utility_a_projects.csv`: five Utility A projects.
- `utility_b_projects.csv`: five Utility B projects.
- `expected_overlap_results.csv`: selected pair checks for a 25-mile threshold, including all three qualifying pairs and two non-overlap examples.

The datasets intentionally include confirmed, candidate, unmatched, and excluded locations. Two projects include endpoint coordinates so the center-point workflow can be tested.

Current app limitation: the upload page stores CSV/XLSX files but does not yet parse them into `st.session_state.projects`. Until import is implemented, use these files as reference data or enter the rows into Project Review manually.
