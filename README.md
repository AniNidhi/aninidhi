# aninidhi

Track which anime have official **Hindi dubs** — across Crunchyroll, Netflix,
Muse India, and Anime Times (Prime Video) — as a Python library and a CLI.

## What's new in v0.2

- **488 real anime/season records**, compiled from each platform's own
  release history as of September 2026 —
  not a placeholder sample anymore.
- **Multi-platform dubs**: the same anime is often dubbed independently by
  more than one platform at different times (e.g. Crunchyroll in 2023,
  then Muse India in 2026). Every anime now carries a `hindi_dubs` list
  instead of a single platform/date pair. **37 titles in this dataset are
  already dubbed on 2+ platforms** — run `aninidhi multi` to see them.
- **Schema room for richer metadata**: `anilist_id`, `anilist_url`,
  `imdb_id`, `imdb_url`, `imdb_rating`, `studio`, `synopsis`,
  `original_title`. These ship as `null` in the bulk-imported data (see
  "Enriching metadata" below) — filling them in per-title wasn't feasible
  as part of a bulk import, so two scripts are included to do it.
- **New functions**: `get_dub_info()`, `multi_platform_dubs()`,
  `platform_stats()`.
- **New CLI commands**: `info`, `multi`, `stats`.

> ⚠️ **Breaking change from v0.0.1**: the old `platform` and
> `hindi_dub_release_date` fields are gone, replaced by `hindi_dubs: [...]`.
> If you wrote code against v0.0.1's schema, see "Migrating from v0.0.1"
> below.

## Install

```bash
pip install aninidhi
```

## Use it as a library

```python
import aninidhi

aninidhi.get_latest(limit=5)              # most recent dub activity, any platform
aninidhi.search("naruto")                 # title search
aninidhi.get_by_platform("crunchyroll")   # anime with a Crunchyroll Hindi dub
aninidhi.get_dub_info("Dan Da Dan")       # full per-platform breakdown for one title
aninidhi.multi_platform_dubs()            # anime dubbed on 2+ platforms
aninidhi.platform_stats()                 # {"Crunchyroll": 298, "Anime Times (Prime Video)": 85, ...}
aninidhi.list_all()                       # everything
```

Every function returns a list of dicts shaped like this:

```json
{
  "id": 83,
  "title": "Dan Da Dan",
  "original_title": null,
  "genres": [],
  "season": null,
  "season_year": null,
  "episodes": null,
  "studio": null,
  "synopsis": null,
  "poster_url": null,
  "mal_id": null,
  "mal_url": null,
  "anilist_id": null,
  "anilist_url": null,
  "imdb_id": null,
  "imdb_url": null,
  "imdb_rating": null,
  "hindi_available": true,
  "hindi_dubs": [
    { "platform": "Anime Times (Prime Video)", "release_date": "2024-10-17", "status": "Finished", "media_type": "series" },
    { "platform": "Crunchyroll", "release_date": "2024-10-25", "status": "Finished", "media_type": "series" },
    { "platform": "Muse India", "release_date": "2024-11-16", "status": "Finished", "media_type": "series" }
  ],
  "notes": null
}
```

## Use it from the command line

```bash
aninidhi latest -n 5
aninidhi search "spy x family"
aninidhi info "Dan Da Dan"          # per-platform breakdown for one title
aninidhi platform crunchyroll
aninidhi multi                      # anime dubbed on 2+ platforms
aninidhi stats                      # dub count per platform
aninidhi all --json
aninidhi refresh --url https://raw.githubusercontent.com/you/aninidhi-data/main/anime.json
```

## Data provenance

The bundled dataset (`src/aninidhi/data/anime.json`) was compiled by
cross-referencing each platform's own release calendar (e.g. Crunchyroll's
Simulcast Calendar). Snapshot date: **September 2026**. It will go stale —
new dubs release every week — so treat it as a strong starting point, not
a live feed:

- Run `aninidhi refresh` against a URL you control (see "Staying fresh")
  to serve updates without republishing the package.
- Consider building the automated polling pipeline described in the
  original project recap (YouTube/RSS/Reddit polling → review queue →
  publish) to keep it current long-term.
- Sony YAY! and JioHotstar are known to carry Hindi-dubbed anime too but
  aren't in this snapshot yet — their catalogs are more TV-schedule-based
  and harder to date precisely from public sources. Good candidates for
  the next data pass.

## Enriching metadata (AniList + IMDb)

The bulk import only had reliable platform/date data, so `genres`,
`synopsis`, `studio`, `episodes`, and the AniList/IMDb ID+URL fields ship
as `null`. Two scripts fill them in, one anime at a time, using each
title as a search query:

```bash
# AniList - free, no API key needed
python scripts/enrich_anilist.py --limit 5   # try a handful first
python scripts/enrich_anilist.py             # then the rest

# IMDb ratings, via the OMDb API (get a free key: https://www.omdbapi.com/apikey.aspx)
export OMDB_API_KEY=your_key_here
python scripts/enrich_imdb.py --limit 5
python scripts/enrich_imdb.py
```

**Neither script has been run against the live APIs** — this environment
has no internet access, so they're written to AniList's and OMDb's
documented interfaces but untested end-to-end. Spot-check a few results
before running either over the full 488 records, and expect some
no-matches on titles with unusual formatting (cour/part splits especially)
since the search is a plain title lookup, not a MAL/AniList ID match.

## Staying fresh

`aninidhi` never requires a server. Point it at any publicly readable
JSON file (a GitHub raw URL is the easiest option, and pairs well with a
daily GitHub Action that regenerates `anime.json`) and it does the rest:

```bash
export ANINIDHI_SOURCE_URL="https://raw.githubusercontent.com/AniNidhi/aninidhi-data/main/anime.json"
```

- If a source URL is set and the local cache (`~/.cache/aninidhi/anime.json`)
  is more than a day old, the next call refreshes it automatically.
- If refreshing fails (offline, source down), it silently falls back to
  whatever's cached, then to the bundled snapshot. A query never raises
  just because the network is unavailable.
- Force an immediate refresh any time with `aninidhi.refresh(force=True)`
  or `aninidhi refresh` on the CLI.

## Migrating from v0.0.1

```python
# v0.0.1
anime["platform"]
anime["hindi_dub_release_date"]

# v0.2
[d["platform"] for d in anime["hindi_dubs"]]
[d["release_date"] for d in anime["hindi_dubs"]]

# convenience: most recent dub date across all platforms
max(d["release_date"] for d in anime["hindi_dubs"])
```

`get_by_platform()` and `get_latest()` keep the same names and signatures
but now search/sort across the whole `hindi_dubs` list under the hood, so
most calling code only needs the field-access changes above.

## Development

```bash
git clone https://github.com/AniNidhi/aninidhi.git
cd aninidhi
pip install -e .
python -m unittest discover -s tests
```

## License

MIT