"""Rule-based planning estimates for a potential shared transmission corridor."""
from __future__ import annotations

import math

COST_REFERENCE_TABLE = {
    "land_acquisition_per_acre": 15000.0,
    "permitting_and_clearing_per_acre": 8500.0,
    "line_construction_per_mile": 1200000.0,
    "shared_corridor_multiplier": 1.3,
    "land_sharing_efficiency": 0.5,
}

DEFAULT_ROW_WIDTH_FEET = 200.0


def calculate_overlap_impact(overlap_length_miles: float, row_width_feet: float) -> dict:
    """Estimate land and construction savings from co-locating two lines."""
    if not math.isfinite(overlap_length_miles) or overlap_length_miles < 0:
        raise ValueError("Overlap length must be a non-negative finite number.")
    if not math.isfinite(row_width_feet) or row_width_feet <= 0:
        raise ValueError("ROW width must be a positive finite number.")

    acres_per_mile_single = (row_width_feet * 5280) / 43560
    total_single_acres = overlap_length_miles * acres_per_mile_single * 2
    shared_acres = total_single_acres * COST_REFERENCE_TABLE["land_sharing_efficiency"]
    land_saved_acres = total_single_acres - shared_acres

    land_cost_per_acre = (
        COST_REFERENCE_TABLE["land_acquisition_per_acre"]
        + COST_REFERENCE_TABLE["permitting_and_clearing_per_acre"]
    )
    separate_land_cost = total_single_acres * land_cost_per_acre
    shared_land_cost = shared_acres * land_cost_per_acre
    separate_build_cost = overlap_length_miles * COST_REFERENCE_TABLE["line_construction_per_mile"] * 2
    shared_build_cost = (
        overlap_length_miles
        * COST_REFERENCE_TABLE["line_construction_per_mile"]
        * COST_REFERENCE_TABLE["shared_corridor_multiplier"]
    )
    total_savings = (separate_land_cost + separate_build_cost) - (shared_land_cost + shared_build_cost)

    rounded_acres = round(land_saved_acres, 2)
    rounded_savings = round(total_savings, 2)
    return {
        "overlap_length_miles": overlap_length_miles,
        "land_saved_acres": rounded_acres,
        "estimated_financial_savings_usd": rounded_savings,
        "explanation": (
            f"By sharing a corridor over {overlap_length_miles:.2f} miles, the utilities "
            f"could save approximately {rounded_acres:.2f} acres of land and "
            f"${rounded_savings:,.2f} in combined land acquisition and construction costs."
        ),
    }