"""The PDF's page text, and the chunks of pages sent to the model."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True)
class Page:
    number: int  # 1-based, as PDF viewers count
    text: str  # pypdf's text, unchanged: the model reads it and the checks compare against it


def read_pages(pdf_path: Path, numbers: Sequence[int] | None = None) -> list[Page]:
    reader = PdfReader(pdf_path)
    count = len(reader.pages)
    wanted = numbers or range(1, count + 1)
    outside = [number for number in wanted if not 1 <= number <= count]
    if outside:
        raise ValueError(f"{pdf_path.name} has {count} pages; asked for {outside[:5]}")
    return [Page(number, reader.pages[number - 1].extract_text() or "") for number in wanted]


def parse_page_ranges(spec: str) -> list[int]:
    """``"171-474,500"`` -> ``[171, 172, ..., 474, 500]``."""
    numbers: set[int] = set()
    for part in spec.split(","):
        first, _, last = part.strip().partition("-")
        start, end = int(first), int(last or first)
        if start < 1 or end < start:
            raise ValueError(f"bad page range {part.strip()!r}")
        numbers.update(range(start, end + 1))
    return sorted(numbers)


def make_chunks(pages: Sequence[Page], max_chars: int) -> list[list[Page]]:
    """Group pages into chunks of up to ``max_chars`` characters of text.

    Each chunk starts on the previous chunk's last page, and has at least two pages even
    if that's over the budget, so a project that runs onto the next page is whole in at
    least one chunk.
    """
    chunks: list[list[Page]] = []
    start = 0
    while start < len(pages):
        end, size = start + 1, len(pages[start].text)
        while end < len(pages) and (end - start < 2 or size + len(pages[end].text) <= max_chars):
            size += len(pages[end].text)
            end += 1
        chunks.append(list(pages[start:end]))
        if end == len(pages):
            break
        start = end - 1
    return chunks


def shifted_chunks(pages: Sequence[Page], max_chars: int) -> list[list[Page]]:
    """Chunks like ``make_chunks``', but with the boundaries moved by half a chunk, so a
    project cut at a boundary of one set of chunks is in the middle of a chunk here."""
    shift = max(1, len(make_chunks(pages, max_chars)[0]) // 2) if pages else 0
    if shift + 1 >= len(pages):
        return make_chunks(pages, max_chars)
    return [list(pages[:shift + 1]), *make_chunks(pages[shift:], max_chars)]


def render(chunk: Sequence[Page]) -> str:
    """The user message for one chunk: each page's text under a ``=== PAGE n ===`` line."""
    return "\n\n".join(f"=== PAGE {page.number} ===\n{page.text}" for page in chunk)
