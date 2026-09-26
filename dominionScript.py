"""Parse Dominion Energy South Carolina's planned transmission projects ($2M and above).

The PDF has one project per page. The output CSV uses the same column names and
formats as data/processed/georgia_power_projects.csv, and the same project IDs as the
Geolocator's project list, so that list's locations and coordinates join on
project_id. Locations, project type and voltages are therefore not parsed here.

Run from the repository root:

    python dominionScript.py
"""

import argparse
import csv
import logging
import re
from pathlib import Path

import pypdf

from parsers.common import extract_miles, normalize_text, parse_us_date

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_PDF = (
    REPO_ROOT / "Sperry-Tech-Challenge" / "Project Listings" / "Dominion Energy"
    / "2024-2028-2million-and-above-project-descriptions.pdf"
)
DEFAULT_OUT = REPO_ROOT / "data" / "processed" / "dominion_projects.csv"

DATE = re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}")
COST_YEARS = [None, 2024, 2025, 2026, 2027, 2028]  # None is "Previous": spent before 2024
COST_COLUMNS = ["cost_previous", "cost_2024", "cost_2025", "cost_2026", "cost_2027", "cost_2028", "cost_total"]
COLUMNS = [
    "project_id", "utility", "sponsor", "state", "project_name", "in_service_date", "start_date",
    "line_miles", "miles_mentioned", "description", *COST_COLUMNS,
]

log = logging.getLogger(__name__)


def text_between(start_label, end_label, text, page_num):
    match = re.search(rf"{start_label}\s+(.*?)\s+{end_label}", text, re.DOTALL | re.IGNORECASE)
    if not match:
        raise ValueError(f"page {page_num + 1}: nothing between {start_label!r} and {end_label!r}")
    return match.group(1).strip()


def extract_utility_projects(pdf_path):
    projects = []

    reader = pypdf.PdfReader(pdf_path)
    for page_num, page in enumerate(reader.pages):
        # One line of text, with the en-dashes in names turned into hyphens
        text = normalize_text(page.extract_text())

        if "Project ID" not in text:
            continue

        # 1. ID sits between "Project ID" and "Project Description".
        # Two IDs have spaces around the dash ("06367 A - C, H"); the Geolocator writes "06367 A-C, H"
        project_id = re.sub(r"\s*-\s*", "-", text_between("Project ID", "Project Description", text, page_num))

        # 2. Date sits between "Planned In-Service Date" and "Estimated Project Cost".
        # Phased projects give one date per phase; the last one is when the whole project is done
        date_text = text_between("Planned In-Service Date", "Estimated Project Cost", text, page_num)
        dates = [parse_us_date(found) for found in DATE.findall(date_text)]
        if not dates:
            raise ValueError(f"page {page_num + 1}: no date in {date_text!r}")

        # 3. Title sits between "5 Year Budget" and "Project ID"
        title = text_between("5 Year Budget", "Project ID", text, page_num)

        # 4. Description sits between "Project Description" and "Project Need"
        description = text_between("Project Description", "Project Need", text, page_num)

        # 5. Costs: the table cells wrap unpredictably, but there are always 7 amounts
        # after the label: Previous, 2024 to 2028, and Total
        cost_text = text.split("Estimated Project Cost", 1)[1]
        costs = [int(amount.replace(",", "")) for amount in re.findall(r"\$([\d,]+)", cost_text)]
        if len(costs) != len(COST_COLUMNS):
            raise ValueError(f"page {page_num + 1}: expected {len(COST_COLUMNS)} cost amounts, found {len(costs)}")
        if sum(costs[:-1]) != costs[-1]:
            log.warning("%s: yearly costs add up to $%s, not the $%s total", project_id, f"{sum(costs[:-1]):,}", f"{costs[-1]:,}")

        # The PDF has no start date, so use January 1 of the first year with spending.
        # Spending under "Previous" means work began before 2024 on an unknown date: leave it blank
        first_year = next((year for year, cost in zip(COST_YEARS, costs) if cost), None)

        miles = extract_miles(f"{title} {description}")  # a few titles give the mileage instead
        projects.append({
            "project_id": project_id,
            "utility": "Dominion Energy South Carolina",
            "sponsor": "DESC",
            "state": "South Carolina",
            "project_name": title,
            "in_service_date": max(dates).isoformat(),
            "start_date": f"{first_year}-01-01" if first_year else "",
            "line_miles": miles[0] if len(miles) == 1 else "",
            "miles_mentioned": "; ".join(f"{m:g}" for m in miles),
            "description": description,
            **dict(zip(COST_COLUMNS, costs)),
        })

    return projects


def main():
    parser = argparse.ArgumentParser(description="Parse the Dominion Energy SC project list into a CSV.")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF, help="project descriptions PDF (default: %(default)s)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output CSV (default: %(default)s)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    projects = extract_utility_projects(args.pdf)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(projects)
    log.info("Wrote %d projects to %s", len(projects), args.out)


if __name__ == "__main__":
    main()
