# Geolocator

`gridlock_desc_locator.py` finds coordinates for each project's location names. A
teammate wrote it (on `origin/Geolocator`), and we extended it before it was merged in
PR #3. Its output columns are described in [data.md](data.md). To run it, follow the
[geocode workflow](../.claude/skills/geocode/SKILL.md).

## Inputs

- **No arguments:** the 44 DESC projects typed into `PROJECTS` by hand from the PDF.
  That's 101 location slots (68 distinct names), up to 4 per project. `utility` and
  `state` come from the `UTILITY` and `STATE` constants.
- **`--projects-csv <file>`:** a parser CSV with `location_1..3`, `voltage_1..2` and
  `project_type`. Only the Georgia Power CSV has these: 353 location slots, 215 distinct
  names. The csv module keeps every value a string, so `09662` keeps its leading zero
  and voltages stay `"115000"`.
- **`--output-prefix`** names the output files (default `desc`).
- **`PROJECT_LIMIT`** at the top of the file: set it to 3 for a quick test and back to
  `None` afterwards.

## How a location is found

1. **Seed.** Nominatim looks up `"<name>, <state>, USA"`, and the first result is the
   seed point. The state is the project's `state`, except for names in
   `LOCATION_STATE_OVERRIDES` (Purrysburg is searched in South Carolina for GA 20277).
   Words in `SEARCH_DROP_WORDS` are left out of the query but kept for scoring. The
   only one is `primary`: Nominatim finds nothing for "Evans Primary", while OSM names
   the substation "Evans Primary Substation".
2. **Candidates.** Overpass returns every `power=substation` node, way and relation
   within 25 km of the seed.
3. **Best match.** Each candidate is scored (below) and the highest score wins.
4. **Fallbacks.** With no candidate, the seed point itself is used, rated LOW. If
   Nominatim found nothing, or its request failed, the row has no coordinates and is
   rated LOW.

## Scoring

| Signal | Points |
|---|---|
| Name equal after normalizing | 6 |
| One name contains the other | 5 |
| Shared words, at least 67% / 40% of all words | 4 / 2 |
| Operator matches one of the utility's `OPERATOR_ALIASES` | 2 |
| Each expected voltage in the `voltage` tag | 1, up to 2 |
| Distance from the seed: up to 2 / 8 / 15 miles | 2 / 1 / 0.5 |

Normalizing lowercases the name, turns `&` into "and", `ft` into "fort" and `st` into
"saint", removes punctuation, and drops generic words (sub, substation, transmission,
station, switching, distribution, tap, line).

Confidence: HIGH from a score of 8, MEDIUM from 5, LOW below that. An unnamed
candidate is never HIGH. Operator, voltage and distance alone can add up to 6, so a
substation with the wrong name can still be rated MEDIUM.

`OPERATOR_ALIASES` is keyed by `utility`. OpenStreetMap tags Georgia substations
"Georgia Power" even around GTC and MEAG projects, so all four Georgia owners accept
that name.

## Cache

`gridlock_geocode_cache.json` holds every Nominatim and Overpass result, under keys
`nominatim::<query>` and `overpass::<lat>,<lon>,<radius>`. It's rewritten after each new
result and committed, so a second run only repeats requests that failed.

- Failed requests aren't cached. The row says "Nominatim request failed; re-run to
  retry" or "Overpass request failed; re-run to retry" (when every Overpass server
  failed), and the next run tries again.
- A `null` Nominatim entry means Nominatim found nothing, and it isn't retried. The
  first version cached failed requests as `null` too, so some of the committed cache's
  7 `null` entries may be errors rather than real misses: Queensboro, Square D, VCS1,
  CIP, North Bridge Terrace, Plumb Branch and VCS2 (all searched in South Carolina).
  Delete a key to retry it.
- The file is overwritten in place. Stopping the run in the middle of a write can leave
  a truncated file, which then loads as an empty cache, and the next run overwrites it.
  Back the cache up before a long run.
- The cache and the output files are read and written relative to the current
  directory, so run the Geolocator from the repo root.

## Rate limits

- Nominatim: at most 1 request per second (the code waits 1.1 s), with a
  `User-Agent` string. That's the public server's usage policy.
- Overpass: `overpass-api.de`, then `overpass.kumi.systems`. Both often return 429 or
  504 errors. Small `around:` queries like these work, but large-area queries tend to
  fail.

## Known wrong or weak lookups

- `EVANS PRIMARY` finds Evans County instead of the town of Evans (Columbia County).
- `MCINTOSH` finds McIntosh County instead of Plant McIntosh (Effingham County).
- LOW rows are often just the town or county Nominatim found (for example "Jasper"
  becomes the middle of Jasper County), and the project's centroid includes them.
  Check `overall_confidence` before trusting a center.
- Georgia's customer-project names and `UNKNOWN` rows (see [data.md](data.md)) aren't
  places. 20466 and 20223 have no location names, so their summary rows have no
  coordinates.
- Why not retry a missing name in the other state: DESC's "North Bridge Terrace"
  searched in Georgia finds a shop in Augusta. Thurmond Dam needs no override, because
  its top result in a Georgia search is the dam on the South Carolina side.

These fixes belong in the planned overrides file
([pipeline.md](pipeline.md#3-manual-overrides-planned)), not in the output CSVs.
