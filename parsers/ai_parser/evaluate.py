"""Score an AI parser CSV against a hand-written parser's CSV of the same PDF.

    python -m parsers.ai_parser.evaluate data/processed/ai/desc_ai_projects.csv data/processed/dominion_projects.csv

Rows are matched on (utility, project_id), preserving IDs as text. Text is compared ignoring
case, spacing and dash style; dates, voltages and mileage exactly. For Georgia Power the
reference's location columns are the parser's guesses from the title, so a difference
there isn't necessarily the AI's mistake.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from parsers.ai_parser.checks import canon, same_text

COMPARED = ["project_name", "sponsor", "in_service_date", "start_date", "line_miles", "miles_mentioned",
            "voltage_1", "voltage_2", "description"]
LOCATIONS = ["location_1", "location_2", "location_3", "other_locations"]
# Blank start dates remain informational: DESC's reference derives them from spending.
KEY_COLUMNS = ["project_name", "in_service_date", "start_date"]
OUTCOMES = ["same", "differ", "blank in AI", "only in AI"]
Identity = tuple[str, str]
Row = dict[str, str]


@dataclass
class Report:
    missing: list[str]  # in the reference, not in the AI CSV
    extra: list[str]  # in the AI CSV, not in the reference
    matched: int
    scores: dict[str, Counter[str]] = field(default_factory=dict)
    differences: list[dict[str, str]] = field(default_factory=list)
    verified: int = 0
    verified_but_wrong: list[str] = field(default_factory=list)
    verified_extra: list[str] = field(default_factory=list)
    verified_differences: Counter[str] = field(default_factory=Counter)  # by column, outside KEY_COLUMNS


def _label(identity: Identity) -> str:
    utility, project_id = identity
    return f"{utility} / {project_id}" if utility else project_id


def _index_rows(rows: Iterable[Row], source: str) -> dict[Identity, Row]:
    indexed = {}
    for row in rows:
        identity = (row.get("utility", ""), row["project_id"])
        if identity in indexed:
            raise ValueError(f"{source}: (utility, project_id) {identity!r} appears twice")
        indexed[identity] = row
    return indexed


def read_csv(path: Path) -> tuple[list[str], dict[Identity, Row]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        missing = [column for column in ("utility", "project_id") if column not in columns]
        if missing:
            raise ValueError(f"{path.name}: missing identity columns: {', '.join(missing)}")
        rows = list(reader)
        # A blank utility is allowed: the AI parser leaves it blank when it can't tell the
        # owner, and the row is then reported as missing and extra rather than stopping the eval
        for line, row in enumerate(rows, start=2):
            if not (row.get("project_id") or "").strip():
                raise ValueError(f"{path.name}: blank project_id on row {line}")
        return columns, _index_rows(rows, path.name)


def outcome(column: str, ai: str, reference: str) -> str:
    if not ai and not reference:
        return "same"
    if not ai:
        return "blank in AI"
    if not reference:
        return "only in AI"
    if column == "line_miles":
        return "same" if float(ai) == float(reference) else "differ"
    if column == "miles_mentioned":
        return "same" if _numbers(ai) == _numbers(reference) else "differ"
    return "same" if same_text(ai, reference) else "differ"


def _numbers(text: str) -> list[float]:
    return [float(part) for part in text.split(";") if part.strip()]


def _locations(row: dict[str, str]) -> str:
    names = [row.get(column, "") for column in LOCATIONS[:3]] + row.get("other_locations", "").split("; ")
    return "; ".join(sorted({canon(name) for name in names if name.strip()}))


def compare(ai_rows: Mapping[object, Row], reference_rows: Mapping[object, Row],
            reference_columns: Sequence[str]) -> Report:
    # Derive keys from the rows even when callers supplied an old ID-only mapping.
    ai_rows = _index_rows(ai_rows.values(), "AI rows")
    reference_rows = _index_rows(reference_rows.values(), "reference rows")
    common = [identity for identity in reference_rows if identity in ai_rows]
    report = Report(
        missing=[_label(identity) for identity in reference_rows if identity not in ai_rows],
        extra=[_label(identity) for identity in ai_rows if identity not in reference_rows],
        matched=len(common),
        verified_extra=[_label(identity) for identity, row in ai_rows.items()
                        if identity not in reference_rows and row.get("status") == "VERIFIED"],
    )
    columns = [column for column in COMPARED if column in reference_columns]
    if "location_1" in reference_columns:
        columns.append("locations")
    for column in columns:
        report.scores[column] = Counter()
    for identity in common:
        utility, project_id = identity
        ai, reference = ai_rows[identity], reference_rows[identity]
        wrong = False
        differ = []
        for column in columns:
            if column == "locations":
                ai_value, reference_value = _locations(ai), _locations(reference)
            else:
                ai_value, reference_value = ai.get(column, ""), reference[column]
            result = outcome(column, ai_value, reference_value)
            report.scores[column][result] += 1
            if result != "same":
                report.differences.append({"utility": utility, "project_id": project_id,
                                           "column": column, "outcome": result,
                                           "ai": ai_value, "reference": reference_value})
                wrong = wrong or (column in KEY_COLUMNS
                                  and not (column == "start_date" and result == "blank in AI"))
                if result == "differ" and column not in KEY_COLUMNS:
                    differ.append(column)
        if ai.get("status") == "VERIFIED":
            report.verified += 1
            report.verified_differences.update(differ)
            if wrong:
                report.verified_but_wrong.append(_label(identity))
    return report


def format_report(report: Report) -> str:
    lines = [
        f"Projects: {report.matched} in both, {len(report.missing)} missing from the AI CSV, "
        f"{len(report.extra)} only in the AI CSV",
    ]
    if report.missing:
        lines.append(f"  missing: {', '.join(report.missing)}")
    if report.extra:
        lines.append(f"  only in the AI CSV: {', '.join(report.extra)}")
    lines.append("")
    lines.append(f"{'column':<18}" + "".join(f"{name:>13}" for name in OUTCOMES))
    for column, counts in report.scores.items():
        lines.append(f"{column:<18}" + "".join(f"{counts[name]:>13}" for name in OUTCOMES))
    lines.append("")
    lines.append(f"VERIFIED matched rows: {report.verified}; of those, {len(report.verified_but_wrong)} "
                 f"disagree with the reference in {', '.join(KEY_COLUMNS)} "
                 "(blank AI start_date excluded)")
    if report.verified_but_wrong:
        lines.append(f"  {', '.join(report.verified_but_wrong)}")
    lines.append(f"VERIFIED rows without a reference identity: {len(report.verified_extra)}")
    if report.verified_extra:
        lines.append(f"  {', '.join(report.verified_extra)}")
    others = ", ".join(f"{column} {count}" for column, count in report.verified_differences.most_common())
    lines.append(f"Other columns where VERIFIED rows differ: {others or 'none'}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m parsers.ai_parser.evaluate",
        description="Compare an AI parser CSV with a hand-written parser's CSV for the same PDF.",
    )
    parser.add_argument("ai_csv", type=Path)
    parser.add_argument("reference_csv", type=Path)
    parser.add_argument("--differences", type=Path, help="also write every difference to this CSV")
    args = parser.parse_args(argv)

    try:
        _, ai_rows = read_csv(args.ai_csv)
        reference_columns, reference_rows = read_csv(args.reference_csv)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Could not read the CSVs: {exc!r}", file=sys.stderr)
        return 1
    report = compare(ai_rows, reference_rows, reference_columns)
    print(format_report(report))
    if args.differences:
        try:
            with args.differences.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["utility", "project_id", "column", "outcome",
                                                           "ai", "reference"])
                writer.writeheader()
                writer.writerows(report.differences)
        except OSError as exc:  # a missing folder, or the file open in Excel
            print(f"Could not write {args.differences}: {exc}", file=sys.stderr)
            return 1
        print(f"\nWrote {len(report.differences)} differences to {args.differences}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
