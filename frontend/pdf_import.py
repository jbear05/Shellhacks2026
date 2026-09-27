"""Deterministic imports of the two organizer PDFs; no AI or geocoding calls."""
from __future__ import annotations

from dataclasses import asdict
from datetime import date
from functools import lru_cache
from hashlib import sha256
from io import BytesIO

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
        from dominionScript import extract_utility_projects
        records = extract_utility_projects(BytesIO(content))
        prefix = "desc"
    else:
        from parsers.georgia_power import parse_georgia_power
        records = [asdict(record) for record in parse_georgia_power(BytesIO(content))]
        records = [row for row in records if row["utility"] == GEORGIA]
        prefix = "georgia_power"
    normalized = [
        {key: value.isoformat() if isinstance(value, date) else "" if value is None else str(value)
         for key, value in row.items()}
        for row in records
    ]
    result = attach_locations(pd.DataFrame(normalized), prefix, SOURCE_FILES[utility])
    result["Source SHA256"] = digest
    return result
