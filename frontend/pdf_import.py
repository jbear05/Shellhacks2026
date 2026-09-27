"""Deterministic imports of the two organizer PDFs; no AI or geocoding calls."""
from __future__ import annotations
from functools import lru_cache
from hashlib import sha256
from parsers.ai_parser.api import parse_pdf

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
        records = parse_pdf(
            content,
            utility=DESC,
            state="South Carolina",
            sponsor="DESC",
        )
        prefix = "desc"
    else:
        records = parse_pdf(
            content,
            utility=GEORGIA,
            state="Georgia",
            pages="171-474",
            workers=4,
        )
        prefix = "georgia_power"

    normalized = []
    for record in records:
        row = dict(record)
        row["Utility"] = utility
        row["Source PDF"] = SOURCE_FILES[utility]
        normalized.append(row)

    result = attach_locations(pd.DataFrame(normalized), prefix, SOURCE_FILES[utility])
    result["Source SHA256"] = digest
    return result
