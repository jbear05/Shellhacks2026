"""Keep the Markdown docs in step with the repo: links resolve, and the tables that list
files and CSV columns match the code."""

import ast
import dataclasses
import re
from pathlib import Path

import pytest

import dominionScript as ds
from parsers import georgia_power as gp

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = sorted(
    [
        *(REPO_ROOT / name for name in ("README.md", "AGENTS.md", "CLAUDE.md")),
        *(REPO_ROOT / "docs").rglob("*.md"),
        *(REPO_ROOT / ".claude" / "skills").rglob("*.md"),
    ]
)
CODE_BLOCK = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
HEADING = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
TABLE_NAME = re.compile(r"^\| `([^`]+)` \|", re.MULTILINE)  # a backticked name in a table's first column


def _text(path):
    return CODE_BLOCK.sub("", path.read_text(encoding="utf-8"))


def _anchors(path):
    """GitHub's anchors for the headings in a Markdown file."""
    return {re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-") for heading in HEADING.findall(_text(path))}


def _section(path, heading):
    return _text(path).split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def _locator_constant(name):
    # Read without importing: importing gridlock_desc_locator loads the geocode cache.
    tree = ast.parse((REPO_ROOT / "gridlock_desc_locator.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(target, "id", None) == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise LookupError(name)


@pytest.mark.parametrize("doc", DOCS, ids=lambda path: path.relative_to(REPO_ROOT).as_posix())
def test_relative_links_resolve(doc):
    broken = []
    for target in LINK.findall(_text(doc)):
        if re.match(r"[a-z]+:", target):  # https:, mailto:
            continue
        path_part, _, anchor = target.partition("#")
        path = (doc.parent / path_part).resolve() if path_part else doc
        if not path.exists() or (anchor and path.suffix == ".md" and anchor not in _anchors(path)):
            broken.append(target)
    assert broken == []


CSV_COLUMNS = {
    "`data/processed/georgia_power_projects.csv`": [field.name for field in dataclasses.fields(gp.ProjectRecord)],
    "`data/processed/dominion_projects.csv`": ds.COLUMNS,
    "`<prefix>_project_locations.csv`": _locator_constant("LOCATION_FIELDS"),
    "`<prefix>_projects_summary.csv`": _locator_constant("SUMMARY_FIELDS"),
}


@pytest.mark.parametrize("heading", CSV_COLUMNS)
def test_data_doc_lists_every_column_in_order(heading):
    assert TABLE_NAME.findall(_section(REPO_ROOT / "docs" / "data.md", heading)) == CSV_COLUMNS[heading]


def test_agents_repo_map_names_existing_paths():
    paths = TABLE_NAME.findall(_section(REPO_ROOT / "AGENTS.md", "Repository map"))
    assert paths
    assert [path for path in paths if not (REPO_ROOT / path).exists()] == []
