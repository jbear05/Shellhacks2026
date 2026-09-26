"""Reviewed sponsor aliases shared by the deterministic and AI parsers."""

from __future__ import annotations


# Georgia ITS plan sponsor codes. Keep this mapping in one place so both parsers
# produce the same utility/project_id join keys. See docs/sources/georgia-power-pdf.md.
GEORGIA_SPONSOR_UTILITY = {
    "GPC": "Georgia Power",
    "SAV": "Georgia Power",  # Savannah area (formerly Savannah Electric)
    "GTC": "Georgia Transmission Corporation",
    "MEAG": "MEAG Power",
    "DU": "Dalton Utilities",
}
