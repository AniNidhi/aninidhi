# aninidhi

Track which anime have official **Hindi dubs** — across Crunchyroll, Netflix,
Muse India, and Prime Video — as a Python library and a CLI.

## What's new in v0.2

- **488 real anime/season records**, not a placeholder sample.
- **Multi-platform dubs**: the same anime is often dubbed independently by
  more than one platform at different times (e.g. Crunchyroll in 2023,
  then Muse India in 2026). Every anime now carries a `hindi_dubs` list
  instead of a single platform/date pair. **37 titles in this dataset are
  already dubbed on 2+ platforms** — run `aninidhi multi` to see them.
- **Schema room for richer metadata**: `anilist_id`, `anilist_url`,
  `imdb_id`, `imdb_url`, `imdb_rating`, `studio`, `synopsis`,
  `original_title`.
- **New functions**: `get_dub_info()`, `multi_platform_dubs()`,
  `platform_stats()`.
- **New CLI commands**: `info`, `multi`, `stats`.

> ⚠️ **Breaking change from v0.0.1**: the old `platform` and
> `hindi_dub_release_date` fields are gone, replaced by `hindi_dubs: [...]`.
> See "Migrating from v0.0.1" below.

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
aninidhi.platform_stats()                 # {"Crunchyroll": 298, "Prime Video": 85, ...}
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
    { "platform": "Prime Video", "release_date": "2024-10-17", "status": "Finished", "media_type": "series" },
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
```

## Staying fresh

`aninidhi` refreshes itself automatically — no setup required. Once a day,
it checks a hosted copy of the dataset and updates its local cache, so you
get new dubs without waiting for a new package release. If it can't reach
the network, it silently falls back to whatever's cached, then to the
snapshot bundled in the package - a query never fails just because you're
offline.

To point it at your own copy of the dataset instead, or to turn off the
automatic check entirely:

```bash
export ANINIDHI_SOURCE_URL="https://raw.githubusercontent.com/you/your-fork/main/anime.json"
# or, to disable the network check completely:
export ANINIDHI_SOURCE_URL=""
```

Force an immediate refresh any time with `aninidhi.refresh(force=True)`
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
but now search/sort across the whole `hindi_dubs` list under the hood.

## Development

```bash
git clone https://github.com/AniNidhi/aninidhi.git
cd aninidhi
pip install -e .
python -m unittest discover -s tests
```

See `CONTRIBUTING.md` for how the dataset is sourced and kept up to date.

## License

MIT