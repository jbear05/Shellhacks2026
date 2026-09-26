"""Read the projects out of any utility project-list PDF with Claude, and check its work.

The model only copies. Each value comes back with the exact text it was read from and the
page that text is on, and ``checks.py`` looks for that text on that page of pypdf's own
output. Dates are re-read from the copied text. A value that fails is left blank and
listed in the review file. Voltages and mileage are worked out here from the checked
title and description, never by the model.

Run from the repository root (docs/ai-parser.md has the details):

    python -m parsers.ai_parser PDF --utility "Dominion Energy South Carolina" --state "South Carolina" --prefix desc_ai
    python -m parsers.ai_parser.evaluate data/processed/ai/desc_ai_projects.csv data/processed/dominion_projects.csv
"""
