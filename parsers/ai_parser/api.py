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
):

    # Temporarily turn the uploaded PDF into a file
    with TemporaryDirectory() as folder:

        pdf_path = Path(folder) / "upload.pdf"
        pdf_path.write_bytes(content)

        page_numbers = (
            parse_page_ranges(pages)
            if pages
            else None
        )

        pdf_pages = read_pages(
            pdf_path,
            page_numbers
        )

    # Tell the parser what utility we're reading
    settings = Settings(
        utility=utility,
        state=state,
        sponsor=sponsor,
        workers=workers,
    )

    # Connect to Claude
    model = Model(
        ResponseCache(CACHE_DIR),
        DEFAULT_MODEL,
        offline=True,
    )
    # Run your existing AI parser
    result = run(
        pdf_pages,
        model.ask,
        settings,
    )

    # Give the frontend normal rows
    return result.rows()