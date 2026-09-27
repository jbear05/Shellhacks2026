"""Programmatic, cache-only replay of a project-list PDF.

The Streamlit app does not call this helper. A missing reply raises ModelError rather
than sending an API request; use the CLI to produce evidence and review files.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from parsers.ai_parser.llm import DEFAULT_MODEL, Model, ResponseCache
from parsers.ai_parser.pages import parse_page_ranges, read_pages
from parsers.ai_parser.pipeline import Settings, run


ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "ai_cache"


def parse_pdf(
    content: bytes,
    utility: str,
    state: str,
    sponsor: str = "",
    pages: str | None = None,
    workers: int = 1,
) -> list[dict[str, str]]:
    """Return checked project rows from cached replies, without writing output files."""
    with TemporaryDirectory() as folder:
        pdf_path = Path(folder) / "upload.pdf"
        pdf_path.write_bytes(content)
        pdf_pages = read_pages(pdf_path, parse_page_ranges(pages) if pages else None)

    settings = Settings(utility=utility, state=state, sponsor=sponsor, workers=workers)
    model = Model(ResponseCache(CACHE_DIR), DEFAULT_MODEL, offline=True)
    return run(pdf_pages, model.ask, settings).rows()
