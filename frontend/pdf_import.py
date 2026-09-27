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
    # The exact PDF hash identifies the committed parser output that was checked
    # against this version of the plan. Keep ownership and IDs from those rows.
    prefix, project_file = (
        ("desc", "dominion_projects.csv") if utility == DESC
        else ("georgia_power", "georgia_power_projects.csv")
    )
    projects = pd.read_csv(ROOT / "data" / "processed" / project_file,
                           dtype=str, keep_default_na=False)
    if utility == GEORGIA:
        projects = projects[projects.utility == GEORGIA]
    result = attach_locations(projects, prefix, SOURCE_FILES[utility])

    result["Source SHA256"] = digest
    return result
