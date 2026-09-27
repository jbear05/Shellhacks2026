# Gridlock

**Find where two power companies plan to build near each other, at the same time.**

Gridlock is our entry for the Sperry Tech challenge at ShellHacks 2026. It reads the
public construction plans of two neighboring utilities, puts every planned
transmission project on a map, and ranks the pairs of projects most worth
coordinating.

## Why it matters

Power companies publish their plans for new and rebuilt transmission lines and
substations, often as long PDF filings with hundreds of pages. When two utilities plan
work close to each other in the same years, they could share a corridor, land, crews
or permits instead of each doing the work alone. These opportunities are hard to find
by hand, because each company's plan is a separate document with its own format.

The challenge compares **Dominion Energy South Carolina (DESC)** and **Georgia
Power**, which meet along the Savannah River. Gridlock looks for:

- **Projects close together:** within 25 miles of each other. This is the main signal.
- **Projects built at the same time:** build windows that overlap. This makes a pair
  stronger.

Most projects won't have a match. The goal is to find the few that do.

## What you get

- **An interactive map** of both utilities' projects. You can pan, zoom and click any
  project or pair for its details.
- **A ranked list of coordination opportunities**, with the strongest pairs first.
- **A land-savings estimate** for pairs of lines that could share one corridor: how many
  acres, and roughly what that land is worth.
- **Downloads** of the project table, the ranked pairs, and a snapshot you can open
  again later.

With the real plans loaded and the default settings, Gridlock finds 73 pairs of projects within 25 miles of
each other. 35 of them also have overlapping build windows, and 25 get a land-savings
estimate.

## How it works

1. **Read the plans.** Gridlock pulls each project out of the utilities' PDFs: its
   name, dates, voltage and description. For another utility's PDF, an optional AI
   reader can do this step, and it checks every value it finds against the page it
   came from.
2. **Find the locations.** Most projects name the substations they connect. Gridlock
   looks those up in OpenStreetMap to place each project on the map. When it can't
   confirm a location, it marks it as low confidence so you know to check it.
3. **Pair nearby projects.** It measures the distance between every DESC project and
   every Georgia Power project, and keeps the pairs within 25 miles.
4. **Rank the pairs.** Each pair gets a score from 0 to 15 based on how close the
   projects are, whether their build windows overlap, how far apart their finish dates
   are, and whether they have similar voltages and types of work.
5. **Estimate the savings.** When both projects are power lines, Gridlock estimates
   the land they would save by sharing one corridor. It uses the lines' lengths,
   typical easement widths and 2026 farmland values from the USDA.

## Try it

You need Python 3.11 or newer.

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -r frontend/requirements.txt
python -m streamlit run app.py
```

The app opens in your browser. Click **Explore the real-data demo** to jump straight
to the results for DESC and Georgia Power. To use your own data, choose **Upload PDFs
or project tables** and follow the steps:

1. **Project Setup:** load the projects. You can use the saved plans, the two
   challenge PDFs, your own CSV or Excel tables, or a snapshot you saved before. Then
   choose the two utilities to compare and the distance to search within.
2. **Project Review:** check and correct project names, dates, voltages and types.
3. **Location Verification:** check where each project is placed, fix a location, or
   leave a project out.
4. **Overlap Results:** explore the map and the ranked list of pairs.
5. **Export Results:** download the tables and a snapshot.

The app only uses data saved on your computer. It never calls a paid AI service or a
map lookup while it runs. The only thing that needs internet is the map's background.

## Good to know

- **Dates come from the filings,** the DESC 2024-2028 plan and Georgia Power's 2025
  plan. They show what was planned then, not what is being built today.
- **Some locations are uncertain.** A project marked LOW confidence may be placed using
  a town's name, or using only one of its two substations. These stay flagged
  everywhere, including in the downloads, so you can check them before relying on a
  pair.
- **Lines on the map are straight connections** between project centers. They are not
  the real routes of the power lines.
- **Only public data is used.** Nothing comes from restricted grid infrastructure data
  (CEII).

## For developers

- [AGENTS.md](AGENTS.md) is a quick tour of the repository, its rules and its commands.
  AI coding agents read it too (Claude Code through [CLAUDE.md](CLAUDE.md)).
- [docs/status.md](docs/status.md) says what's done, what's next and who owns which
  branch.
- [docs/pipeline.md](docs/pipeline.md) explains each step above in detail, and
  [docs/data.md](docs/data.md) describes every column of every data file.
- The challenge brief, guide and source PDFs are in `Sperry-Tech-Challenge/`, summarized
  in [docs/challenge.md](docs/challenge.md).

The tools behind the app can also run on their own:

```bash
python -m parsers.georgia_power                      # read the Georgia Power plan (all sponsors)
python -m parsers.georgia_power --sponsors GPC SAV   # only Georgia Power's own projects
python dominionScript.py                             # read the DESC plan
python gridlock_desc_locator.py                      # find locations (calls public map servers)
python -m parsers.ai_parser PDF --utility "Georgia Power" --state Georgia --prefix georgia_power_ai --dry-run
pytest -m "not slow"                                 # quick tests, about 15 s
pytest                                               # all tests, about 50 s
```

Read [docs/geolocator.md](docs/geolocator.md) before running the location finder, and
[docs/ai-parser.md](docs/ai-parser.md) before running the AI reader. The AI reader costs
money unless you use `--dry-run` (an estimate only) or `--offline` (replays saved
answers).
