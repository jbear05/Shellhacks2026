"""A rough land-value impact for a coordination opportunity (the challenge's bonus).

If two nearby projects shared land, the smaller one's footprint could be shared. The
estimate is that footprint times the average of the two states' farm real estate values.
The land values come from USDA; the footprints are an assumed rule, not source data.
"""
from __future__ import annotations

from typing import Any, Mapping

from ranking import _project_type

LAND_VALUE_SOURCE = (
    "USDA NASS, Land Values 2026 Summary (July 2026), page 9: "
    "farm real estate average value per acre, 2026"
)
LAND_VALUE_PER_ACRE = {"Georgia": 4950, "South Carolina": 4900}
UTILITY_STATES = {"Dominion Energy South Carolina": "South Carolina", "Georgia Power": "Georgia"}
# Assumed acres per project, by the ranking's project type (MULTI_LINE is LINE, MULTI_SITE is BOTH).
FOOTPRINT_ACRES = {"LINE": 0.5, "SUBSTATION": 1.0, "BOTH": 1.5}


def utility_state(utility: Any, region: Any = "") -> str:
    """The project's state: its region when that is a state with a value, else the utility's."""
    region = str(region or "").strip()
    return region if region in LAND_VALUE_PER_ACRE else UTILITY_STATES.get(str(utility or "").strip(), "")


def land_value_per_acre(state: str) -> int | None:
    return LAND_VALUE_PER_ACRE.get(state)


def footprint_acres(project_type: Any) -> float | None:
    return FOOTPRINT_ACRES.get(_project_type(str(project_type or "")))


def estimate_overlap_impact(pair: Mapping[str, Any]) -> dict[str, Any]:
    """Estimate columns for one overlap row; None where a type or state is unknown."""
    estimate: dict[str, Any] = {}
    for suffix in ("a", "b"):
        state = utility_state(pair.get(f"utility_{suffix}"), pair.get(f"region_{suffix}"))
        estimate[f"utility_state_{suffix}"] = state
        estimate[f"land_value_per_acre_{suffix}"] = land_value_per_acre(state)
        estimate[f"estimated_acres_{suffix}"] = footprint_acres(pair.get(f"project_type_{suffix}"))
    acres = [estimate["estimated_acres_a"], estimate["estimated_acres_b"]]
    values = [estimate["land_value_per_acre_a"], estimate["land_value_per_acre_b"]]
    shared = min(acres) if None not in acres else None
    value = sum(values) / 2 if None not in values else None
    estimate["estimated_shared_acres"] = shared
    estimate["estimated_land_value_per_acre"] = value
    estimate["estimated_land_savings_usd"] = shared * value if shared is not None and value is not None else None
    return estimate
