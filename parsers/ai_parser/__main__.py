"""Command line: python -m parsers.ai_parser PDF --utility ... --state ... --prefix ..."""

from __future__ import annotations

import argparse
import hashlib
import logging
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from pypdf.errors import PdfReadError

from parsers.ai_parser.llm import DEFAULT_MODEL, PRICES, Model, ModelError, ResponseCache
from parsers.ai_parser.pages import Page, parse_page_ranges, read_pages, render
from parsers.ai_parser.pipeline import ParseError, Settings, chunks_for, run, write_outputs

log = logging.getLogger("parsers.ai_parser")

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "data" / "processed" / "ai"
DEFAULT_CACHE_DIR = REPO_ROOT / "data" / "ai_cache"
# For --dry-run's estimate: (tokens of prompt and schema per request, characters of
# page text per token), fitted to the first 55 requests (2026-09-26)
INPUT_TOKENS = {"extract": (1_270, 1.75), "inventory": (650, 2.0)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m parsers.ai_parser",
        description="Read the projects out of a utility's project-list PDF with Claude or Gemini, "
                    "checking every value against the PDF's own text. See docs/ai-parser.md.",
    )
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--utility", required=True,
                        help='document utility; project sponsors can resolve to other owners, e.g. "Georgia Power"')
    parser.add_argument("--state", required=True, help='written to every row, e.g. "South Carolina"')
    parser.add_argument("--sponsor", default="", help="for rows where the PDF prints no sponsor, e.g. DESC")
    parser.add_argument("--prefix", required=True, help="output file names start with this, e.g. desc_ai")
    parser.add_argument("--pages", help="only these pages, e.g. 171-474 or 1-5,9 (default: all)")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help="a Claude model, or a gemini-* one such as gemini-3.8-flash (default: %(default)s)")
    parser.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"],
                        help="how much the model thinks during extraction; Gemini treats xhigh and max "
                             "as high (default: %(default)s)")
    parser.add_argument("--chunk-chars", type=int, default=12_000,
                        help="characters of page text per request (default: %(default)s)")
    parser.add_argument("--workers", type=int, default=1, help="requests at a time (default: %(default)s)")
    parser.add_argument("--no-inventory", action="store_true", help="skip the ID pass that cross-checks completeness")
    parser.add_argument("--no-fallback", action="store_true",
                        help="don't let the API retry a declined request on another model (Claude only)")
    parser.add_argument("--offline", action="store_true", help="use only cached replies; fail if one is missing")
    parser.add_argument("--dry-run", action="store_true", help="show the requests a run would make, and stop")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="default: %(default)s")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR, help="default: %(default)s")
    parser.add_argument("-v", "--verbose", action="store_true", help="log debug output")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s")
    if not args.verbose:
        for client_log in ("httpx2", "httpx"):  # Claude's and Gemini's HTTP clients
            logging.getLogger(client_log).setLevel(logging.WARNING)  # one line per request otherwise

    if not args.pdf.is_file():
        parser.error(f"PDF not found: {args.pdf}")
    settings = Settings(
        utility=args.utility, state=args.state, sponsor=args.sponsor, chunk_chars=args.chunk_chars,
        effort=args.effort, inventory=not args.no_inventory, workers=args.workers,
    )
    model = Model(ResponseCache(args.cache_dir), args.model, offline=args.offline, fallback=not args.no_fallback)
    try:
        pages = read_pages(args.pdf, parse_page_ranges(args.pages) if args.pages else None)
    except (PdfReadError, ValueError) as exc:  # not a PDF, or a bad --pages
        log.error("Could not read %s: %s", args.pdf.name, exc)
        return 1
    try:
        if args.dry_run:
            dry_run(pages, settings, model)
            return 0
        result = run(pages, model.ask, settings)
    except (ParseError, ModelError) as exc:
        log.error("Could not parse %s: %s", args.pdf.name, exc)
        return 1

    run_info = {
        "source_pdf": _display_path(args.pdf),
        "pdf_sha256": hashlib.sha256(args.pdf.read_bytes()).hexdigest(),
        "pages": args.pages or "all",
        "model": args.model,
        "answered_by": dict(model.answered_by),  # differs from "model" if the API's fallback answered
    }
    try:
        written = write_outputs(result, args.out_dir, args.prefix, run_info)
    except OSError as exc:  # e.g. the CSV is open in Excel
        log.error("Could not write the output: %s", exc)
        return 1

    statuses = Counter(project.status for project in result.projects)
    log.info("Read %d projects: %d VERIFIED, %d NEEDS_REVIEW", len(result.projects),
             statuses["VERIFIED"], statuses["NEEDS_REVIEW"])
    log.info("%d problems to review, %d of them not tied to a project",
             len(result.review_rows()), len(result.problems))
    for other, count in model.answered_by.items():
        if other != args.model:
            log.warning("%d replies were written by %s, the API's fallback, not %s", count, other, args.model)
    if model.requests:
        cost = model.cost()
        log.info("Made %d requests: %s input and %s output tokens%s", model.requests,
                 f"{model.tokens('input_tokens'):,}", f"{model.tokens('output_tokens'):,}",
                 f" (about ${cost:.2f})" if cost is not None else "")
    else:
        log.info("Every reply came from the cache")
    for path in written:
        log.info("Wrote %s", _display_path(path))
    return 0


def dry_run(pages: Sequence[Page], settings: Settings, model: Model) -> None:
    for name, (task, chunks) in chunks_for(pages, settings).items():
        chunks = model.request_chunks(task, chunks)
        to_send = [chunk for chunk in chunks if not model.is_cached(task, chunk)]
        per_request, chars_per_token = INPUT_TOKENS[name]
        tokens = sum(per_request + len(render(chunk)) / chars_per_token for chunk in to_send)
        print(f"{name}: {len(chunks)} requests ({len(chunks) - len(to_send)} cached); "
              f"the rest send about {tokens:,.0f} input tokens")
    if model.is_gemini:
        print("Those counts are fitted to Claude's tokenizer, so Gemini's will differ.")
    prices = PRICES.get(model.model)
    ratio = f"{prices[1] / prices[0]:g} times as much" if prices else "more"
    print(f"Output tokens cost {ratio} and depend on the number of projects: "
          "DESC's 44 took Claude about 12,000, Georgia Power's 208 about 120,000.")


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
