"""Merge the checked fragments into one row per project, and collect what needs review.

A value is kept only if its quote is on the page it cites (and, for a date, the date is
in the quote). Anything else is left blank and becomes a row of the review file, and so
does every disagreement between two places in the PDF.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field

from parsers.ai_parser.checks import PageText, canon, check_date, locate, normalize_id, same_text
from parsers.ai_parser.schema import DateQuote, Fragment, Quote
from parsers.common import extract_miles, extract_voltages
from parsers.utilities import GEORGIA_SPONSOR_UTILITY

# The shared columns of both parser CSVs, plus the columns gridlock_desc_locator.py
# --projects-csv reads, so this CSV can go straight to the Geolocator.
COLUMNS = [
    "project_id", "utility", "sponsor", "state", "project_name", "project_type",
    "location_1", "location_2", "location_3", "other_locations", "voltage_1", "voltage_2",
    "in_service_date", "start_date", "line_miles", "miles_mentioned", "description",
    "pages", "status",
]
REVIEW_COLUMNS = ["project_id", "field", "value", "quote", "page", "reason"]
VERIFIED, NEEDS_REVIEW = "VERIFIED", "NEEDS_REVIEW"
REQUIRED = ("project_name", "in_service_date")
YEARS = range(1990, 2061)
MAX_MILES = 300


@dataclass(frozen=True)
class Problem:
    """One row of the review file."""

    project_id: str
    field: str
    reason: str
    value: str = ""
    quote: str = ""
    page: int | None = None


@dataclass(frozen=True)
class Accepted:
    """A value that passed its checks, and the quote it came from."""

    value: str
    quote: str
    page: int


@dataclass
class Project:
    project_id: str
    fields: dict[str, Accepted] = field(default_factory=dict)  # project_name, sponsor, in_service_date, start_date
    description: Accepted | None = None
    locations: list[Accepted] = field(default_factory=list)
    pages: set[int] = field(default_factory=set)
    problems: list[Problem] = field(default_factory=list)

    @property
    def status(self) -> str:
        return NEEDS_REVIEW if self.problems else VERIFIED

    def value(self, name: str) -> str:
        return self.fields[name].value if name in self.fields else ""

    def add(self, problem: Problem) -> None:
        # Chunks share a page, so the same fragment, and the same problem, can come twice
        if problem not in self.problems:
            self.problems.append(problem)

    def flag(self, name: str, reason: str, quote: Quote | None = None, value: str = "") -> None:
        self.add(Problem(
            self.project_id, name, reason, value, quote.text if quote else "", quote.page if quote else None))


def merge(fragments: Iterable[Fragment], pages: PageText) -> tuple[dict[str, Project], list[Problem]]:
    """Check every fragment's values and merge the fragments that share a project ID.

    Fragments are taken in page order, so when two places disagree the earlier page wins
    (for Georgia Power, that's Table 2). Returns the
    projects and the problems that belong to no project.
    """
    projects: dict[str, Project] = {}
    stray: list[Problem] = []
    for fragment in sorted(fragments, key=lambda fragment: fragment.project_id.page):
        id_text, why = locate(pages, fragment.project_id)
        if id_text is None:
            problem = Problem(
                normalize_id(fragment.project_id.text), "project_id", f"project ID {why}; its fragment was dropped",
                quote=fragment.project_id.text, page=fragment.project_id.page)
            if problem not in stray:
                stray.append(problem)
            continue
        project = projects.setdefault(normalize_id(id_text), Project(normalize_id(id_text)))
        project.pages.add(fragment.project_id.page)
        for name in ("project_name", "sponsor"):
            _merge_text(project, name, getattr(fragment, name), pages)
        for name in ("in_service_date", "start_date"):
            _merge_date(project, name, getattr(fragment, name), pages)
        _merge_description(project, fragment.description, pages)
        _merge_locations(project, fragment.locations, pages)
    # A dropped fragment of a project that was read elsewhere still casts doubt on it
    for problem in list(stray):
        if problem.project_id in projects:
            projects[problem.project_id].add(problem)
            stray.remove(problem)
    return projects, stray


def _accept(project: Project, name: str, new: Accepted) -> None:
    project.pages.add(new.page)
    old = project.fields.setdefault(name, new)
    if old is not new and not same_text(old.value, new.value):
        project.add(Problem(
            project.project_id, name,
            f"page {old.page} says {old.value!r} but page {new.page} says {new.value!r}; keeping page {old.page}",
            new.value, new.quote, new.page))


def _merge_text(project: Project, name: str, quote: Quote | None, pages: PageText) -> None:
    if quote is None:
        return
    value, why = locate(pages, quote)
    if value is None:
        project.flag(name, why, quote)
    else:
        _accept(project, name, Accepted(value, quote.text, quote.page))


def _merge_date(project: Project, name: str, quote: DateQuote | None, pages: PageText) -> None:
    if quote is None:
        return
    text, why = locate(pages, quote)
    if text is None:
        project.flag(name, why, quote, quote.iso or "")
        return
    value, why = check_date(quote)
    if value is None:
        project.flag(name, why, quote, quote.iso or "")
    else:
        _accept(project, name, Accepted(value.isoformat(), quote.text, quote.page))


def _merge_description(project: Project, pieces: Sequence[Quote], pages: PageText) -> None:
    if not pieces:
        return
    values = []
    for piece in pieces:
        value, why = locate(pages, piece)
        if value is None:  # half a description would mislead, so drop the whole of this one
            project.flag("description", why, piece)
            return
        values.append(value)
    new = Accepted(" ".join(values), " ".join(piece.text for piece in pieces), pieces[0].page)
    project.pages.update(piece.page for piece in pieces)
    old = project.description
    if old is None or canon(old.value) in canon(new.value):
        project.description = new  # a chunk that saw the page after gives the longer, whole text
    elif canon(new.value) not in canon(old.value):
        project.add(Problem(
            project.project_id, "description",
            f"page {new.page} gives a different description from page {old.page}; keeping page {old.page}",
            new.value, new.quote, new.page))


def _merge_locations(project: Project, quotes: Sequence[Quote], pages: PageText) -> None:
    for quote in quotes:
        value, why = locate(pages, quote)
        if value is None:
            project.flag("locations", why, quote)
        elif not any(same_text(value, known.value) for known in project.locations):
            project.locations.append(Accepted(value, quote.text, quote.page))


def sanity_problems(project: Project) -> list[Problem]:
    """Values that passed their checks but look wrong, or are missing."""
    problems = []
    flagged = {problem.field for problem in project.problems}
    for name in REQUIRED:
        if name not in project.fields and name not in flagged:
            problems.append(Problem(project.project_id, name, "not found in the document"))
    for name in ("in_service_date", "start_date"):
        if name in project.fields and int(project.value(name)[:4]) not in YEARS:
            accepted = project.fields[name]
            problems.append(Problem(
                project.project_id, name, f"year outside {YEARS.start}-{YEARS.stop - 1}",
                accepted.value, accepted.quote, accepted.page))
    start, end = project.value("start_date"), project.value("in_service_date")
    if start and end and start > end:
        accepted = project.fields["start_date"]
        problems.append(Problem(
            project.project_id, "start_date", f"starts after its in-service date {end}",
            start, accepted.quote, accepted.page))
    if any(miles > MAX_MILES for miles in extract_miles(_title_and_description(project))):
        problems.append(Problem(project.project_id, "miles_mentioned", f"mentions more than {MAX_MILES} miles"))
    return problems


def inventory_problems(projects: dict[str, Project], listed: Iterable[Quote], pages: PageText) -> list[Problem]:
    """Compare the extraction with the ID pass, which read the pages with other chunk boundaries.

    A project the ID pass didn't list gets a problem; an ID it listed that nothing was read
    for is returned as a problem of its own. IDs the ID pass got wrong are ignored: it's
    only a cross-check.
    """
    found: dict[str, int] = {}
    for quote in listed:
        text, _ = locate(pages, quote)
        if text is not None:
            found.setdefault(normalize_id(text), quote.page)
    for project in projects.values():
        if project.project_id not in found:
            project.flag("project_id", "the ID pass didn't list this project")
    return [
        Problem(project_id, "project_id", "listed by the ID pass, but no project was read for it", page=page)
        for project_id, page in found.items()
        if project_id not in projects
    ]


def page_problems(labels: dict[int, set[str]], projects: dict[str, Project], numbers: Iterable[int]) -> list[Problem]:
    """Pages the model didn't label, or labelled as project pages without reading a project from them."""
    cited = {page for project in projects.values() for page in project.pages}
    problems = []
    for number in numbers:
        kinds = labels.get(number, set())
        if not kinds:
            problems.append(Problem("", "page", "the model didn't label this page", page=number))
        elif kinds & {"project_list", "project_detail"} and number not in cited:
            problems.append(Problem(
                "", "page", f"labelled {' and '.join(sorted(kinds))}, but no project was read from it", page=number))
    return problems


def _title_and_description(project: Project) -> str:
    return f"{project.value('project_name')} {project.description.value if project.description else ''}"


def project_utility(project: Project, document_utility: str, default_sponsor: str) -> tuple[str, str]:
    """Resolve an owner without replacing a different printed sponsor with the document owner.

    The Georgia Power document includes several utilities. Its reviewed aliases are
    shared with the deterministic parser. Unknown aliases retain their source text
    and need review; the caller's default is used for an otherwise unlabelled document.
    """
    sponsor = project.value("sponsor") or default_sponsor
    if canon(document_utility) == "georgia power":
        aliases = {canon(code): owner for code, owner in GEORGIA_SPONSOR_UTILITY.items()}
        aliases.update({canon(owner): owner for owner in GEORGIA_SPONSOR_UTILITY.values()})
        if canon(sponsor) in aliases:
            return aliases[canon(sponsor)], ""
        if not sponsor:
            return "", "no sponsor found in a mixed-utility plan; utility left blank"
        return sponsor, "unknown Georgia sponsor; utility kept as printed sponsor pending review"
    if not sponsor or same_text(sponsor, document_utility) or (
        default_sponsor and same_text(sponsor, default_sponsor)
    ):
        return document_utility, ""
    return sponsor, "unmapped sponsor differs from document utility; utility kept as printed sponsor pending review"


def utility_problems(project: Project, document_utility: str, default_sponsor: str) -> list[Problem]:
    utility, reason = project_utility(project, document_utility, default_sponsor)
    if not reason:
        return []
    source = project.fields.get("sponsor")
    return [Problem(project.project_id, "utility", reason, utility,
                    source.quote if source else "", source.page if source else None)]


def to_row(project: Project, utility: str, state: str, default_sponsor: str) -> dict[str, str]:
    """The CSV row. Voltages and mileage are worked out here, from the checked title and
    description, the way both hand-written parsers do it; the model never supplies them."""
    name = project.value("project_name")
    description = project.description.value if project.description else ""
    voltages = [*(extract_voltages(name) or extract_voltages(description)), None, None]
    miles = extract_miles(_title_and_description(project))
    locations = [location.value for location in project.locations]
    padded = [*locations, "", "", ""]
    return {
        "project_id": project.project_id,
        "utility": project_utility(project, utility, default_sponsor)[0],
        "sponsor": project.value("sponsor") or default_sponsor,
        "state": state,
        "project_name": name,
        "project_type": "",
        "location_1": padded[0],
        "location_2": padded[1],
        "location_3": padded[2],
        "other_locations": "; ".join(locations[3:]),
        "voltage_1": str(voltages[0] or ""),
        "voltage_2": str(voltages[1] or ""),
        "in_service_date": project.value("in_service_date"),
        "start_date": project.value("start_date"),
        "line_miles": str(miles[0]) if len(miles) == 1 else "",
        "miles_mentioned": "; ".join(f"{m:g}" for m in miles),
        "description": description,
        "pages": "; ".join(map(str, sorted(project.pages))),
        "status": project.status,
    }


def review_row(problem: Problem) -> dict[str, str]:
    row = asdict(problem)
    row["page"] = "" if problem.page is None else str(problem.page)
    return {column: row[column] for column in REVIEW_COLUMNS}


def evidence(project: Project) -> dict:
    """Everything a person needs to trace the row back to the PDF."""
    return {
        "project_id": project.project_id,
        "status": project.status,
        "pages": sorted(project.pages),
        "fields": {name: asdict(accepted) for name, accepted in project.fields.items()},
        "description": asdict(project.description) if project.description else None,
        "locations": [asdict(location) for location in project.locations],
        "problems": [asdict(problem) for problem in project.problems],
    }
