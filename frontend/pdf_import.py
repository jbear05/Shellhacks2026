"""Deterministic imports of the two organizer PDFs; no AI or geocoding calls."""
from __future__ import annotations
from functools import lru_cache
from hashlib import sha256


import pandas as pd

from frontend.data_loader import ProjectLoadError
from frontend.project_data import DESC, GEORGIA, ROOT, SOURCE_FILES, attach_locations


@lru_cache(maxsize=2)
def source_digest(utility: str) -> str:
    return sha256((ROOT / SOURCE_FILES[utility]).read_bytes()).hexdigest()


def parse_known_pdf(content: bytes) -> pd.DataFrame:
    """Require the exact public source before reusing its saved location evidence."""
    digest = sha256(content).hexdigest()
    utility = next((name for name in SOURCE_FILES if source_digest(name) == digest), None)
    if utility is None:
        raise ProjectLoadError(
            "This PDF is not one of the two supported organizer files. Upload the DESC "
            "2024–2028 project descriptions or Georgia Power 2025 IRP Volume 3 public PDF, "
            "or import a CSV/XLSX project table. Revised PDFs need their locations reviewed first."
        )
    if utility == DESC:
        ai_data = pd.read_csv(
            ROOT / "data" / "processed" / "ai" / "desc_ai_projects.csv",
            dtype=str,
            keep_default_na=False,
        )

        old_data = pd.read_csv(
            ROOT / "data" / "processed" / "dominion_projects.csv",
            dtype=str,
            keep_default_na=False,
        )

        old_data = old_data.set_index("project_id")

        for field in ("start_date", "project_type", "voltage_2"):
            if field in ai_data.columns and field in old_data.columns:
                ai_data[field] = ai_data.apply(
                    lambda row: (
                        row[field]
                        if row[field]
                        else old_data[field].get(row["project_id"], "")
                    ),
                    axis=1,
                )

        records = ai_data.to_dict("records")

        prefix = "desc"
    else:
        records = pd.read_csv(
            ROOT / "data" / "processed" / "georgia_power_projects.csv",
            dtype=str,
            keep_default_na=False,
        ).to_dict("records")
        records = [
            row for row in records
            if row.get("utility") == GEORGIA
        ]
        prefix = "georgia_power"

    normalized = []

    for record in records:
        row = dict(record)
        row["Utility"] = utility
        row["Source PDF"] = SOURCE_FILES[utility]
        normalized.append(row)

    result = attach_locations(
        pd.DataFrame(normalized),
        prefix,
        SOURCE_FILES[utility]
    )

    result["Source SHA256"] = digest
    return result
