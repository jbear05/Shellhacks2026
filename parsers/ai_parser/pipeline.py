"""Run the passes over a PDF's pages and write the three output files."""

from __future__ import annotations

import csv
import json
import logging
from collections import defaultdict
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from parsers.ai_parser.checks import PageText
from parsers.ai_parser.llm import AnswerTooLong, Task, extraction_task, inventory_task
from parsers.ai_parser.pages import Page, make_chunks, shifted_chunks, split_chunk
from parsers.ai_parser.records import (
    COLUMNS, REVIEW_COLUMNS, Problem, Project, evidence, inventory_problems, merge, page_problems,
    review_row, sanity_problems, to_row, utility_problems,
)

log = logging.getLogger(__name__)

Ask = Callable[[Task, Sequence[Page]], BaseModel]


class ParseError(Exception):
    """The run can't produce a CSV, for example because no page has any text."""


@dataclass(frozen=True)
class Settings:
    utility: str
    state: str
    sponsor: str = ""  # for rows whose document doesn't print a sponsor
    chunk_chars: int = 12_000
    effort: str = "high"
    inventory: bool = True  # run the ID pass as a cross-check
    workers: int = 1  # requests at a time


@dataclass
class Result:
    projects: list[Project]  # in page order
    problems: list[Problem]  # the ones that belong to no project
    page_labels: dict[int, list[str]]
    skipped_pages: list[int]
    settings: Settings

    def rows(self) -> list[dict[str, str]]:
        return [to_row(project, self.settings.utility, self.settings.state, self.settings.sponsor)
                for project in self.projects]

    def review_rows(self) -> list[dict[str, str]]:
        problems = [problem for project in self.projects for problem in project.problems] + self.problems
        return [review_row(problem) for problem in problems]


def chunks_for(pages: Sequence[Page], settings: Settings) -> dict[str, tuple[Task, list[list[Page]]]]:
    """The requests a run makes, by pass. The ID pass's chunk boundaries fall mid-chunk of
    the extraction's, so a project cut in two by one pass is whole in the other."""
    readable = [page for page in pages if page.text.strip()]
    passes = {"extract": (extraction_task(settings.effort), make_chunks(readable, settings.chunk_chars))}
    if settings.inventory:
        passes["inventory"] = (inventory_task(), shifted_chunks(readable, settings.chunk_chars))
    return passes


def run(pages: Sequence[Page], ask: Ask, settings: Settings) -> Result:
    readable = [page for page in pages if page.text.strip()]
    skipped = [page.number for page in pages if not page.text.strip()]
    if not readable:
        raise ParseError("no page has any text; a scanned PDF needs OCR first")
    for number in skipped:
        log.warning("Page %d has no text (a scanned page?) and was skipped", number)
    text = PageText(readable)
    passes = chunks_for(readable, settings)

    task, chunks = passes["extract"]
    extracted = _ask_all(ask, task, chunks, settings.workers)
    labels: dict[int, set[str]] = defaultdict(set)
    for chunk, reply in extracted:
        numbers = {page.number for page in chunk}
        for label in reply.pages:
            if label.page in numbers:
                labels[label.page].add(label.kind)
    projects, problems = merge((fragment for _, reply in extracted for fragment in reply.projects), text)

    if settings.inventory:
        task, chunks = passes["inventory"]
        listed = [quote for _, reply in _ask_all(ask, task, chunks, settings.workers) for quote in reply.project_ids]
        problems += inventory_problems(projects, listed, text)
    problems += page_problems(labels, projects, [page.number for page in readable])
    for project in projects.values():
        project.problems.extend(sanity_problems(project))
        project.problems.extend(utility_problems(project, settings.utility, settings.sponsor))

    ordered = sorted(projects.values(), key=lambda project: (min(project.pages), project.project_id))
    return Result(ordered, problems, {page: sorted(kinds) for page, kinds in sorted(labels.items())}, skipped, settings)


def _ask_all(ask: Ask, task: Task, chunks: Sequence[list[Page]], workers: int) -> list[tuple[list[Page], Any]]:
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        replies = list(pool.map(lambda chunk: _ask_chunk(ask, task, chunk), chunks))
    return [pair for pairs in replies for pair in pairs]


def _ask_chunk(ask: Ask, task: Task, chunk: list[Page]) -> list[tuple[list[Page], Any]]:
    """Ask for one chunk; if the reply is too long, ask for each half (sharing a page) instead."""
    try:
        return [(chunk, ask(task, chunk))]
    except AnswerTooLong:
        if len(chunk) == 1:
            raise ParseError(f"the {task.name} reply for page {chunk[0].number} alone is too long") from None
        first, second = split_chunk(chunk)
        log.info("The %s reply for pages %d-%d was too long; asking for each half",
                 task.name, chunk[0].number, chunk[-1].number)
        return _ask_chunk(ask, task, first) + _ask_chunk(ask, task, second)


def write_outputs(result: Result, out_dir: Path, prefix: str, run_info: dict[str, Any]) -> list[Path]:
    """``<prefix>_projects.csv``, ``<prefix>_review.csv`` and ``<prefix>_evidence.json``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    projects_csv = out_dir / f"{prefix}_projects.csv"
    review_csv = out_dir / f"{prefix}_review.csv"
    evidence_json = out_dir / f"{prefix}_evidence.json"
    _write_csv(projects_csv, COLUMNS, result.rows())
    _write_csv(review_csv, REVIEW_COLUMNS, result.review_rows())
    report = {
        **run_info,
        "settings": asdict(result.settings),
        "skipped_pages": result.skipped_pages,
        "page_labels": result.page_labels,
        "projects": [evidence(project) for project in result.projects],
        "other_problems": [asdict(problem) for problem in result.problems],
    }
    evidence_json.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return [projects_csv, review_csv, evidence_json]


def _write_csv(path: Path, columns: Sequence[str], rows: Sequence[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
