"""Parse Georgia Power's 10-Year Transmission Plan out of the 2025 IRP, Volume 3.

The 668-page IRP PDF embeds the "2024 GA ITS Ten-Year Plan". Two parts of it hold
the project data:

* Table 2, "Georgia ITS 10 Year Plan Project List": one row per planned project
  with zone, plan year, TEAMS number, name, need date and sponsor. Costs are
  redacted in the public filing.
* Section IV detail pages: one page per project, keyed by TEAMS number, adding a
  start date and a free-text scope description.

The two are joined on TEAMS number. Locations, project type and voltages are
derived from each project title with heuristics, in the columns that
gridlock_desc_locator.py --projects-csv reads, so the output can feed the geocoder.

Run from the repository root:

    python -m parsers.georgia_power
    python -m parsers.georgia_power --sponsors GPC SAV --out data/processed/gpc_only.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
from bisect import bisect_right
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, fields
from datetime import date
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from parsers.common import extract_miles, extract_voltages, normalize_text, parse_us_date
from parsers.utilities import GEORGIA_SPONSOR_UTILITY as SPONSOR_UTILITY

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = (
    REPO_ROOT / "Sperry-Tech-Challenge" / "Project Listings" / "Georgia Power"
    / "2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf"
)
DEFAULT_OUT = REPO_ROOT / "data" / "processed" / "georgia_power_projects.csv"

STATE = "Georgia"
class ParseError(Exception):
    """The PDF no longer has the structure this parser relies on."""


def _parse_date(text: str, teams: str) -> date:
    try:
        return parse_us_date(text)
    except ValueError as exc:
        raise ParseError(f"TEAMS {teams}: {exc}") from exc


# --------------------------------------------------------------------------- page text

SECTION_BOOKMARK = re.compile(r"Ten Year Plan", re.IGNORECASE)
BOILERPLATE = (
    re.compile(r"CRITICAL ENERGY INFRASTRUCTURE INFORMATION.*?employees\.", re.DOTALL),
    re.compile(r"\d{4} GA ITS Ten-Year Plan \(\d{4}-\d{4}\)\s+Page \d+ of \d+"),
    re.compile(r"PUBLIC DISCLOSURE"),
    re.compile(r"Zone Year TEAMS.*?DU Totals", re.DOTALL),  # Table 2 header, repeated on every page
)


@dataclass(frozen=True)
class PagedText:
    """Cleaned text of consecutive PDF pages, joined into one string."""

    text: str
    page_starts: tuple[int, ...]
    first_page: int

    def page_at(self, offset: int) -> int:
        """Return the 1-based PDF page number that contains character ``offset``."""
        return self.first_page + bisect_right(self.page_starts, offset) - 1


def join_pages(pages: Sequence[str], first_page: int) -> PagedText:
    starts, offset = [], 0
    for page in pages:
        starts.append(offset)
        offset += len(page) + 1  # +1 for the "\n" separator
    return PagedText("\n".join(pages), tuple(starts), first_page)


def clean_page_text(text: str) -> str:
    """Remove the banner, footer and table header that pypdf repeats on every page."""
    for pattern in BOILERPLATE:
        text = pattern.sub("", text)
    return text


def bookmarked_page_range(reader: PdfReader, title: re.Pattern[str]) -> tuple[int, int]:
    """Return the 1-based, inclusive page range of the first bookmark whose title matches."""
    bookmarks = [
        (item.title, reader.get_destination_page_number(item) + 1)
        for item in _flatten(reader.outline)
    ]
    for name, first in bookmarks:
        if title.search(name):
            later = [page for _, page in bookmarks if page > first]
            return first, (min(later) - 1 if later else len(reader.pages))
    raise ParseError(f"no bookmark matching {title.pattern!r}; has the IRP layout changed?")


def _flatten(outline: Iterable) -> Iterable:
    for item in outline:
        if isinstance(item, list):
            yield from _flatten(item)
        else:
            yield item


def load_plan_text(pdf_path: Path) -> PagedText:
    reader = PdfReader(pdf_path)
    first, last = bookmarked_page_range(reader, SECTION_BOOKMARK)
    log.info("Ten-Year Plan is on PDF pages %d-%d; extracting text", first, last)
    pages = [clean_page_text(reader.pages[i].extract_text() or "") for i in range(first - 1, last)]
    return join_pages(pages, first)


# --------------------------------------------------------------------------- Table 2

DATE = r"\d{1,2}/\d{1,2}/\d{2,4}"
TABLE_CAPTION = "Table 2 Georgia ITS 10 Year Plan Project List"
TABLE_END = re.compile(r"^Total\s+REDACTED", re.MULTILINE)
ROW_START = re.compile(r"^\d{3} 20\d\d \d{4,6} ", re.MULTILINE)
TABLE_ROW = re.compile(
    r"^(?P<zone>\d{3}) (?P<year>20\d\d) (?P<teams>\d{4,6}) (?P<name>.+?)\s*"
    rf"(?P<need>{DATE}) (?P<sponsor>[A-Z]{{2,5}})\s+REDACTED",
    re.MULTILINE | re.DOTALL,
)
LEAKED_TEXT = re.compile(r"REDACTED|Estimated Cost|Zone Year|TEAMS")


@dataclass(frozen=True)
class TableRow:
    teams: str
    zone: str
    plan_year: int
    name: str
    need_date: date
    sponsor: str
    page: int


def parse_project_table(doc: PagedText) -> list[TableRow]:
    """Parse Table 2.

    Project names wrap over several lines, so each row is matched from its
    zone/year/TEAMS start to its date/sponsor/REDACTED end instead of line by line.
    """
    start = doc.text.find(TABLE_CAPTION)
    if start < 0:
        raise ParseError(f"table caption {TABLE_CAPTION!r} not found")
    # Stopping at the Total row keeps the Cancelled/Completed tables that follow it out.
    end_match = TABLE_END.search(doc.text, start)
    if end_match is None:
        raise ParseError("end of Table 2 (the 'Total REDACTED ...' row) not found")
    end = end_match.start()

    rows = [
        TableRow(
            teams=m["teams"],
            zone=m["zone"],
            plan_year=int(m["year"]),
            name=normalize_text(m["name"]),
            need_date=_parse_date(m["need"], m["teams"]),
            sponsor=m["sponsor"],
            page=doc.page_at(m.start()),
        )
        for m in TABLE_ROW.finditer(doc.text, start, end)
    ]

    expected = len(ROW_START.findall(doc.text, start, end))
    if not rows:
        raise ParseError("Table 2 has no rows")
    if len(rows) != expected:
        raise ParseError(
            f"Table 2 has {expected} row starts but {len(rows)} complete rows; a row's layout changed"
        )
    leaked = [row.teams for row in rows if LEAKED_TEXT.search(row.name)]
    if leaked:
        raise ParseError(f"Table 2 rows swallowed neighbouring text: TEAMS {leaked}")
    duplicates = sorted(teams for teams, n in Counter(r.teams for r in rows).items() if n > 1)
    if duplicates:
        raise ParseError(f"duplicate TEAMS numbers in Table 2: {duplicates}")
    return rows


# --------------------------------------------------------------------------- detail pages

DETAIL_HEADER = re.compile(
    r"^[^\n]*\n[ \t]*Teams # (?P<teams>\d+)[ \t]*\n"
    rf"[ \t]*Need Date (?P<need>{DATE}) Start Date (?P<start>{DATE})",
    re.MULTILINE,
)
# Fixed form text on every detail page. What remains after removing it is always:
# description, REDACTED (supporting statement), change vs previous plan, change vs previous IRP.
FORM_TEXT = (
    re.compile(r"Estimated Cost\s*[–-]\s*ITS\s*Assigned\*\s*REDACTED"),
    re.compile(r"Estimated Cost\s*[–-]\s*(?:GPC|GTC|MEAG|DU)\s*REDACTED"),
    re.compile(r"\* The ITS Assigned designation is for parity forecast purposes only"),
    re.compile(
        r"^[ \t]*(?:Description|Supporting Statement|Change From Previous Ten Year Plan"
        r"|Change From Previous IRP)[ \t]*$",
        re.MULTILINE,
    ),
)
SUPPORTING_STATEMENT = "REDACTED"


@dataclass(frozen=True)
class ProjectDetail:
    teams: str
    need_date: date
    start_date: date
    description: str
    change_from_previous_plan: str
    change_from_previous_irp: str
    page: int


def parse_details(doc: PagedText) -> dict[str, ProjectDetail]:
    """Parse the Section IV detail pages, keyed by TEAMS number.

    pypdf emits each page's form labels first and their values afterwards, and a long
    description can push part of the cost block onto the next page. So each project's
    text is cut out first (header to next header) and the fixed form text removed,
    rather than matching labels to values.
    """
    headers = list(DETAIL_HEADER.finditer(doc.text))
    details: dict[str, ProjectDetail] = {}
    for header, following in zip(headers, [*headers[1:], None]):
        teams = header["teams"]
        chunk = doc.text[header.end() : following.start() if following else len(doc.text)]
        for pattern in FORM_TEXT:
            chunk = pattern.sub("", chunk)
        lines = [line.strip() for line in chunk.splitlines() if line.strip()]
        if SUPPORTING_STATEMENT not in lines:
            raise ParseError(f"TEAMS {teams}: no redacted supporting statement on its detail page")
        cut = lines.index(SUPPORTING_STATEMENT)
        changes = [*lines[cut + 1 : cut + 3], "", ""]
        if teams in details:
            raise ParseError(f"TEAMS {teams} has more than one detail page")
        details[teams] = ProjectDetail(
            teams=teams,
            need_date=_parse_date(header["need"], teams),
            start_date=_parse_date(header["start"], teams),
            description=normalize_text(" ".join(lines[:cut])),
            change_from_previous_plan=changes[0],
            change_from_previous_irp=changes[1],
            page=doc.page_at(header.start()),
        )
    return details


# --------------------------------------------------------------------------- titles

OWNER_TAGS = frozenset({"APC", "FPL", "GPC", "GTC", "MEAG", "SAV", "USA"})
TITLE_PREFIX = re.compile(r"^(?:(?:SAV|GTC|MEAG|DU|GPC)\s*:|(?:CC|GRID)\s+-)\s*")  # sponsor / program
TITLE_FIXES = (  # abbreviations and typos seen in Table 2 titles
    (re.compile(r"(?<=\d\d)O(?=\s*KV)"), "0"),  # "23O KV"
    (re.compile(r"\bV\.\s*RICA\b"), "VILLA RICA"),
    (re.compile(r"\bPRI\b\.?"), "PRIMARY"),
    (re.compile(r"\bRD\b\.?"), "ROAD"),
    (re.compile(r"\bTALLBOT\b"), "TALBOT"),
)
PARENTHETICAL = re.compile(r"\(([^)]*)\)")
VOLTAGE_TOKEN = re.compile(r"\b\d{2,3}(?:\s*[/-]\s*\d{2,3})*\s*KV\b")
AT_SITE = re.compile(r"^.*?\bAT\s+")  # "SMART VALVES AT EAST VILLA RICA ..."
DASH = re.compile(r"\s+-\s*|\s*-\s+|(?<=[A-Z.])-(?=[A-Z])")
SITE_JOINER = re.compile(r"\s+(?:AND|&)\s+|\s*[,:]\s*")
CIRCUIT_NUMBER = re.compile(r"#\s*\d+")
LOOP_IN = re.compile(r"\bLOOP[- ]?IN\b|\bFOLD[- ]?IN\b")
BARE_VOLTAGE = re.compile(r"(?:46|69|115|230|500)(?:/\d{2,3})?")  # "THOMASTON 230 NEW BUILD SUB"
DIRECTIONS = {"N": "NORTH", "S": "SOUTH", "E": "EAST", "W": "WEST"}
# Words that begin the description of the work rather than a place name.
WORK_WORDS = frozenset(
    """
    AKA AREA AUTO AUTOBANK BANK BREAKER BUS BUSES CAP CAPACITOR CC CONVERSION CUSTOMER DATA
    DUAL EQUIPMENT EXPANSION HALF IMPROVEMENT IMPROVEMENTS IMPROVMNT INSTALLATION JUMPER
    LIMITING LOOP LOW MODERNIZATION MODIFICATION NEEDS NETWORK PANEL PARTIAL PROJECT
    PROTECTIVE REACTOR REACTORS REBUILD RECONDUCTOR RELAY RELAYING REMOVAL REPLACEMENT
    SECOND SERIES SMART SOLUTION STATCOM STATION STRATEGIC SUB SUBSTATION SWITCHING TIE
    TRANSFORMER TRANSFORMERS TRANSMISSION TRAP UPGRADE UPGRADES XFMR 2ND
    """.split()
)
# ...except these, which also start real place names ("NEW CAVENDER DRIVE", "SWITCH WAY", "LINE CREEK").
WORK_WORDS_UNLESS_FIRST = frozenset({"LINE", "LINES", "NEW", "SWITCH"})


@dataclass(frozen=True)
class TitleInfo:
    locations: tuple[str, ...]
    owner_tags: tuple[str, ...]
    project_type: str
    voltages: tuple[int, ...]


def parse_title(title: str) -> TitleInfo:
    """Derive place names, owner tags, project type and voltages from a Table 2 title.

    This is a heuristic: it handles the common "A - B 115KV REBUILD" shape and the
    single-site shapes in the 2024 plan, but results should be reviewed before geocoding.
    """
    text = normalize_text(title).upper()
    for pattern, replacement in TITLE_FIXES:
        text = pattern.sub(replacement, text)
    voltages = tuple(extract_voltages(text))
    project_is_loop_in = bool(LOOP_IN.search(text))

    while prefix := TITLE_PREFIX.match(text):
        text = text[prefix.end() :]
    tags = tuple(dict.fromkeys(t.strip() for t in PARENTHETICAL.findall(text) if t.strip() in OWNER_TAGS))
    text = PARENTHETICAL.sub(" ", text)
    text = VOLTAGE_TOKEN.split(text, maxsplit=1)[0]  # everything after the voltage describes the work
    text = AT_SITE.sub("", text)

    sites_per_segment = [
        sites
        for segment in DASH.split(text)
        if (sites := [site for part in SITE_JOINER.split(segment) if (site := _clean_site(part))])
    ]
    locations = tuple(dict.fromkeys(site for sites in sites_per_segment for site in sites))

    if project_is_loop_in:
        project_type = "BOTH"
    elif not sites_per_segment:
        project_type = "UNKNOWN"
    elif len(sites_per_segment) == 1:
        project_type = "MULTI_SITE" if len(sites_per_segment[0]) > 1 else "SUBSTATION"
    else:
        project_type = "LINE" if len(sites_per_segment) == 2 else "MULTI_LINE"
    return TitleInfo(locations, tags, project_type, voltages)


def _clean_site(text: str) -> str:
    words: list[str] = []
    for word in CIRCUIT_NUMBER.sub(" ", text).split():
        key = word.rstrip(".")
        if key in WORK_WORDS or (words and key in WORK_WORDS_UNLESS_FIRST):
            break
        if not BARE_VOLTAGE.fullmatch(word):
            words.append(word)
    if len(words) > 1 and words[0] in DIRECTIONS:
        words[0] = DIRECTIONS[words[0]]
    return " ".join(words).strip(" .,-&")


# --------------------------------------------------------------------------- output

@dataclass(frozen=True)
class ProjectRecord:
    """One output row. The location, type and voltage columns are what the Geolocator reads."""

    project_id: str  # TEAMS number
    utility: str
    sponsor: str
    state: str
    project_name: str
    project_type: str  # heuristic: LINE, MULTI_LINE, SUBSTATION, MULTI_SITE, BOTH or UNKNOWN
    location_1: str
    location_2: str
    location_3: str
    other_locations: str
    voltage_1: int | None  # volts
    voltage_2: int | None
    in_service_date: date  # Table 2 need date
    start_date: date | None
    plan_year: int
    zone: str
    owner_tags: str  # owners named in the title: "USA" = federal, "APC" = Alabama Power, "SAV"/"GPC" = Georgia Power
    line_miles: float | None  # only when the description mentions exactly one mileage
    miles_mentioned: str
    description: str
    change_from_previous_plan: str
    change_from_previous_irp: str
    detail_need_date: date | None
    table_page: int
    detail_page: int | None


def build_records(rows: Sequence[TableRow], details: dict[str, ProjectDetail]) -> list[ProjectRecord]:
    records = []
    for row in rows:
        detail = details.get(row.teams)
        description = detail.description if detail else ""
        title = parse_title(row.name)
        voltages = [*(title.voltages or extract_voltages(description)), None, None]
        locations = [*title.locations, "", "", ""]
        miles = extract_miles(description)
        records.append(
            ProjectRecord(
                project_id=row.teams,
                utility=SPONSOR_UTILITY.get(row.sponsor, row.sponsor),
                sponsor=row.sponsor,
                state=STATE,
                project_name=row.name,
                project_type=title.project_type,
                location_1=locations[0],
                location_2=locations[1],
                location_3=locations[2],
                other_locations="; ".join(title.locations[3:]),
                voltage_1=voltages[0],
                voltage_2=voltages[1],
                in_service_date=row.need_date,
                start_date=detail.start_date if detail else None,
                plan_year=row.plan_year,
                zone=row.zone,
                owner_tags="; ".join(title.owner_tags),
                line_miles=miles[0] if len(miles) == 1 else None,
                miles_mentioned="; ".join(f"{m:g}" for m in miles),
                description=description,
                change_from_previous_plan=detail.change_from_previous_plan if detail else "",
                change_from_previous_irp=detail.change_from_previous_irp if detail else "",
                detail_need_date=detail.need_date if detail else None,
                table_page=row.page,
                detail_page=detail.page if detail else None,
            )
        )
    return records


def find_inconsistencies(rows: Sequence[TableRow], details: dict[str, ProjectDetail]) -> list[str]:
    """Data problems in the source PDF itself; worth knowing about, but not fatal."""
    problems = []
    table_teams = {row.teams for row in rows}
    for row in rows:
        detail = details.get(row.teams)
        if detail is None:
            problems.append(f"TEAMS {row.teams}: no detail page")
        else:
            if detail.need_date != row.need_date:
                problems.append(
                    f"TEAMS {row.teams}: need date is {row.need_date} in Table 2 but "
                    f"{detail.need_date} on its detail page (using Table 2)"
                )
            if not detail.description:
                problems.append(f"TEAMS {row.teams}: empty description")
        if row.sponsor not in SPONSOR_UTILITY:
            problems.append(f"TEAMS {row.teams}: unknown sponsor {row.sponsor!r}")
    problems.extend(f"TEAMS {teams}: detail page but no Table 2 row" for teams in sorted(set(details) - table_teams))
    return problems


def parse_georgia_power(pdf_path: Path) -> list[ProjectRecord]:
    """Parse the IRP PDF into one record per Ten-Year Plan project."""
    doc = load_plan_text(pdf_path)
    rows = parse_project_table(doc)
    details = parse_details(doc)
    log.info("Parsed %d Table 2 rows and %d detail pages", len(rows), len(details))
    for problem in find_inconsistencies(rows, details):
        log.warning("%s", problem)
    return build_records(rows, details)


def write_csv(records: Sequence[ProjectRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[field.name for field in fields(ProjectRecord)])
        writer.writeheader()
        writer.writerows(asdict(record) for record in records)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse the Georgia Power Ten-Year Plan into a CSV.")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF, help="IRP Volume 3 PDF (default: %(default)s)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output CSV (default: %(default)s)")
    parser.add_argument(
        "--sponsors",
        nargs="+",
        choices=sorted(SPONSOR_UTILITY),
        help="keep only these sponsors, e.g. 'GPC SAV' for Georgia Power itself (default: all)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="log debug output")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s")

    if not args.pdf.is_file():
        parser.error(f"PDF not found: {args.pdf}")
    try:
        records = parse_georgia_power(args.pdf)
    except (ParseError, PdfReadError) as exc:
        log.error("Could not parse %s: %s", args.pdf.name, exc)
        return 1

    if args.sponsors:
        records = [record for record in records if record.sponsor in args.sponsors]
    try:
        write_csv(records, args.out)
    except OSError as exc:  # e.g. the CSV is open in Excel
        log.error("Could not write %s: %s", args.out, exc)
        return 1
    log.info("Wrote %d projects to %s", len(records), args.out)
    log.info("By sponsor: %s", dict(Counter(r.sponsor for r in records).most_common()))
    log.info("By project type: %s", dict(Counter(r.project_type for r in records).most_common()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
