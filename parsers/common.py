"""Text helpers shared by the utility-plan parsers."""

from __future__ import annotations

import re
from datetime import date, datetime

_DASHES = str.maketrans({"‒": "-", "–": "-", "—": "-", "−": "-"})
# "230KV", "115 kV", "230/115KV", "230- 115KV", "115-13.8 kV"
_VOLTAGE = re.compile(r"(\d{1,3}(?:\.\d+)?(?:\s*[/-]\s*\d{1,3}(?:\.\d+)?)*)\s*kV\b", re.IGNORECASE)
# "5.45 miles", "1 mile", "(2.23mi)", "10mile", "~15 - mile"
_MILES = re.compile(r"(\d+(?:\.\d+)?)\s*-?\s*(?:miles?|mi)\b", re.IGNORECASE)


def normalize_text(text: str) -> str:
    """Collapse all whitespace to single spaces and turn typographic dashes into hyphens."""
    return " ".join(text.translate(_DASHES).split())


def parse_us_date(text: str) -> date:
    """Parse ``m/d/yyyy`` or ``m/d/yy``; raise ``ValueError`` for anything else."""
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"not an m/d/y date: {text!r}")


def extract_voltages(text: str) -> list[int]:
    """Return the distinct voltages written as kV in ``text``, in volts, highest first."""
    volts = {
        round(float(value) * 1000)
        for group in _VOLTAGE.findall(text)
        for value in re.split(r"\s*[/-]\s*", group)
    }
    return sorted(volts, reverse=True)


def extract_miles(text: str) -> list[float]:
    """Return every mileage figure mentioned in ``text``, in order of appearance."""
    return [float(value) for value in _MILES.findall(text)]
