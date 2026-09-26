"""Check the model's copied text against pypdf's text of the page it cites."""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import date

from parsers.ai_parser.pages import Page
from parsers.ai_parser.schema import DateQuote, Quote
from parsers.common import normalize_text, parse_us_date

_US_DATE = re.compile(r"\b\d{1,2}/\d{1,2}/(?:\d{4}|\d{2})\b")
_ISO_DATE = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_NAMED_MONTH_DATE = re.compile(r"\b([A-Za-z]{3,9})\.? (\d{1,2}),? (\d{4})\b")  # "December 31, 2025"
_MONTHS = {name: number for number, name in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def canon(text: str) -> str:
    """How quotes are compared: whitespace collapsed, dashes as hyphens, case ignored."""
    return normalize_text(text).lower()


def squash(text: str) -> str:
    """``canon`` without any spaces, for text that pypdf ran together or split apart."""
    return "".join(canon(text).split())


def same_text(first: str, second: str) -> bool:
    return canon(first) == canon(second) or squash(first) == squash(second)


def normalize_id(text: str) -> str:
    """A project ID as a join key. The spaces around ``-`` go, as in dominionScript.py:
    ``06367 A - C, H`` becomes ``06367 A-C, H``, which is how the Geolocator spells it."""
    return re.sub(r"\s*-\s*", "-", normalize_text(text))


class PageText:
    """pypdf's text of every page in the run, for looking quotes up."""

    def __init__(self, pages: Sequence[Page]):
        self._plain = {page.number: normalize_text(page.text) for page in pages}
        self._lower = {number: text.lower() for number, text in self._plain.items()}
        self._squashed = {number: text.replace(" ", "") for number, text in self._lower.items()}
        # Where each character of the squashed text is in the lowered text, so a match
        # that ignored spacing can be mapped back to the page's own characters
        self._kept = {number: [at for at, char in enumerate(text) if char != " "]
                      for number, text in self._lower.items()}

    def __contains__(self, number: object) -> bool:
        return number in self._plain

    def find(self, text: str, page: int) -> str | None:
        """The page's own spelling of ``text`` if it's on ``page`` as whole words, otherwise None.

        Case and dash style are ignored, and so is spacing when that's all that differs
        (pypdf splits some words at line ends and runs others together).
        """
        if page not in self._plain or not text.strip():
            return None
        plain, lower = self._plain[page], self._lower[page]
        needle = canon(text)
        spans = ((at, at + len(needle)) for at in _occurrences(lower, needle))
        needle = squash(text)
        kept = self._kept[page]
        spans_ignoring_spaces = (
            (kept[at], kept[at + len(needle) - 1] + 1) for at in _occurrences(self._squashed[page], needle))
        for start, end in (*spans, *spans_ignoring_spaces):
            if _whole_words(lower, start, end):
                # lower() keeps the length for everything these PDFs contain, but not for every character
                return plain[start:end] if len(lower) == len(plain) else normalize_text(text)
        return None

    def pages_with(self, text: str) -> list[int]:
        return [number for number in self._plain if self.find(text, number) is not None]


def _occurrences(text: str, needle: str):
    at = text.find(needle)
    while at >= 0:
        yield at
        at = text.find(needle, at + 1)


def _whole_words(text: str, start: int, end: int) -> bool:
    """False if the span starts or ends inside a word or number: "Lee" in "Leesville"."""
    cuts_in = start > 0 and text[start - 1].isalnum() and text[start].isalnum()
    cuts_out = end < len(text) and text[end].isalnum() and text[end - 1].isalnum()
    return not (cuts_in or cuts_out)


def locate(pages: PageText, quote: Quote) -> tuple[str | None, str]:
    """``(value, "")`` when the quote is on its page, else ``(None, why not)``."""
    found = pages.find(quote.text, quote.page)
    if found is not None:
        return found, ""
    if not quote.text.strip():
        return None, "empty text"
    if quote.page not in pages:
        return None, f"cites page {quote.page}, which wasn't in this run"
    elsewhere = pages.pages_with(quote.text)
    if elsewhere:
        return None, f"not on page {quote.page}, but on page {', '.join(map(str, elsewhere[:3]))}"
    return None, f"not on page {quote.page} or any other page"


def dates_in(text: str) -> list[date]:
    """Every date written in ``text`` as m/d/y, YYYY-MM-DD or "Month d, yyyy", in order."""
    text = normalize_text(text)
    found: list[tuple[int, date]] = []
    for match in _US_DATE.finditer(text):
        try:
            found.append((match.start(), parse_us_date(match.group())))
        except ValueError:
            pass
    for match in _ISO_DATE.finditer(text):
        try:
            found.append((match.start(), date(*map(int, match.groups()))))
        except ValueError:
            pass
    for match in _NAMED_MONTH_DATE.finditer(text):
        month = _MONTHS.get(match.group(1)[:3].lower())
        if month:
            try:
                found.append((match.start(), date(int(match.group(3)), month, int(match.group(2)))))
            except ValueError:
                pass
    return [value for _, value in sorted(found, key=lambda pair: pair[0])]


def check_date(quote: DateQuote) -> tuple[date | None, str]:
    """``(date, "")`` when the model's ISO date is one of the dates in its quote, else ``(None, why not)``."""
    if quote.iso is None:
        return None, f"{quote.text!r} gives no day, so it isn't turned into a date"
    try:
        value = date.fromisoformat(quote.iso)
    except ValueError:
        return None, f"{quote.iso!r} isn't a YYYY-MM-DD date"
    printed = dates_in(quote.text)
    if not printed:
        return None, f"no date this program can read in {quote.text!r} to check {quote.iso} against"
    if value not in printed:
        return None, f"{quote.iso} isn't a date in {quote.text!r}"
    return value, ""
