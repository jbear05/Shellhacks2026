"""The bonus estimate: land two nearby lines could save by sharing one corridor.

If both lines ran in one corridor for the shorter line's length, the narrower of their
two easements would no longer be needed there. That is an upper bound: it assumes the
whole shorter line could share the corridor. The acres are priced at the two states'
average farm real estate value. The distance between the two projects is not a
corridor length, so it isn't used.
"""
from __future__ import annotations

from typing import Any, Mapping

from ranking import _number, _project_type, _voltage

LAND_VALUE_SOURCE = "USDA NASS, Land Values 2026 Summary (July 2026), page 9, farm real estate average value per acre in 2026"
LAND_VALUE_URL = "https://www.nass.usda.gov/Publications/Todays_Reports/reports/land0726.pdf#page=9"
LAND_VALUE_PER_ACRE = {"Georgia": 4950, "South Carolina": 4900}
UTILITY_STATES = {"Dominion Energy South Carolina": "South Carolina", "Georgia Power": "Georgia"}

ROW_WIDTH_SOURCE = "Georgia Transmission Corporation, Transmission Line Heights and Easement Widths (2017), typical cross-country easement widths"
ROW_WIDTH_URL = "https://www.gatransmission.com/wp-content/uploads/2017/09/GTC_PoleHeightsFactSheet.pdf"
# The narrowest cross-country width for each voltage (230 kV H-frame is 125 feet, 500 kV up to 180).
ROW_WIDTH_FEET = {115000: 100, 230000: 100, 500000: 150}
SQUARE_FEET_PER_ACRE = 43560
FEET_PER_MILE = 5280

IMPACT_COLUMNS = ["state_a", "state_b", "shared_miles", "row_width_feet", "land_saved_acres",
                  "land_value_per_acre", "land_saved_value_usd", "impact_explanation"]


def project_state(utility: Any, region: Any = "") -> str:
    """The project's state: its region when that is a state with a value, else the utility's."""
    region = str(region or "").strip()
    return region if region in LAND_VALUE_PER_ACRE else UTILITY_STATES.get(str(utility or "").strip(), "")


def estimate_overlap_impact(pair: Mapping[str, Any]) -> dict[str, Any]:
    """IMPACT_COLUMNS for one overlap row; the numbers are None when a project lacks an input."""
    states, miles, widths, missing = [], [], [], []
    for suffix in ("a", "b"):
        project = pair.get(f"project_id_{suffix}")
        state = project_state(pair.get(f"utility_{suffix}"), pair.get(f"region_{suffix}"))
        length = _number(str(pair.get(f"line_miles_{suffix}") or ""))
        volts = _voltage(str(pair.get(f"voltage_{suffix}") or ""))
        states.append(state)
        miles.append(length)
        widths.append(ROW_WIDTH_FEET.get(int(volts)) if volts else None)
        if _project_type(str(pair.get(f"project_type_{suffix}") or "")) not in {"LINE", "BOTH"}:
            missing.append(f"{project} is not line work")
        elif not length or length <= 0:
            missing.append(f"{project} has no single line length in its plan")
        elif widths[-1] is None:
            missing.append(f"{project}'s voltage has no typical easement width")
        if state not in LAND_VALUE_PER_ACRE:
            missing.append(f"{project} is in no state with a land value")
    estimate = dict.fromkeys(IMPACT_COLUMNS)
    estimate.update(state_a=states[0], state_b=states[1])
    if missing:
        estimate["impact_explanation"] = "No estimate: " + "; ".join(missing) + "."
        return estimate
    shared_miles = min(miles)
    width = min(widths)
    acres = shared_miles * FEET_PER_MILE * width / SQUARE_FEET_PER_ACRE
    value = (LAND_VALUE_PER_ACRE[states[0]] + LAND_VALUE_PER_ACRE[states[1]]) / 2
    estimate.update(shared_miles=shared_miles, row_width_feet=width, land_saved_acres=acres,
                    land_value_per_acre=value, land_saved_value_usd=acres * value)
    estimate["impact_explanation"] = (
        f"If both lines shared one corridor for the shorter line's {shared_miles:g} miles, "
        f"the narrower {width}-foot easement would not be needed there: about {acres:,.1f} acres, "
        f"worth roughly ${acres * value:,.0f} at ${value:,.0f} an acre."
    )
    return estimate
