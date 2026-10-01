# aninidhi

Track which anime have official **Hindi dubs** — across Crunchyroll, Netflix,
Muse India, Prime Video, and JioHotstar — as a Python library and a CLI.

## What's new in v0.3.0

- **Series & Season Breakdown (`aninidhi series <title>`)**: Query a franchise name (e.g. `aninidhi series Slime`) to see all available seasons, overall status, and a per-platform breakdown.
- **Airing Dubs Tracker (`aninidhi airing`)**: Quickly list anime currently airing Hindi dub episodes.
- **Python API Additions**: New `get_series_info(title)` and `get_airing()` functions.
- **Unquoted CLI Queries**: Pass multi-word anime titles directly without requiring quotation marks (`aninidhi series That Time I Got Reincarnated as a Slime`).
- **Cleaned & Consolidated Dataset**: Deduplicated multi-batch entries into clean Season-level objects with episode ranges stored in platform dub objects.

## Install

```bash
pip install aninidhi
```

## Use it as a library

```python
import aninidhi

aninidhi.get_series_info("Slime")         # full franchise & season breakdown
aninidhi.get_airing()                     # all anime currently marked as Airing
aninidhi.get_latest(limit=5)              # most recent dub activity, any platform
aninidhi.search("naruto")                 # title search
aninidhi.get_by_platform("crunchyroll")   # anime with a Crunchyroll Hindi dub
aninidhi.get_dub_info("Dan Da Dan")       # full per-platform breakdown for one title
aninidhi.multi_platform_dubs()            # anime dubbed on 2+ platforms
aninidhi.platform_stats()                 # {"Crunchyroll": 298, "Prime Video": 85, ...}
aninidhi.list_all()                       # everything
```

Every function returns a list of dicts (or series info object) shaped like this:

```json
{
  "id": 480,
  "title": "That Time I Got Reincarnated as a Slime (Season 4)",
  "status": "Airing",
  "season": 4,
  "hindi_available": true,
  "hindi_dubs": [
    { "platform": "Crunchyroll", "release_date": "2026-07-31", "status": "Finished", "media_type": "series", "episodes": "EP 1-10" },
    { "platform": "Anime Times (Prime Video)", "release_date": "2026-06-02", "status": "Airing", "media_type": "series" },
    { "platform": "Muse India", "release_date": "2026-08-29", "status": "Airing", "media_type": "series" }
  ]
}
```

## Use it from the command line

```bash
aninidhi series That Time I Got Reincarnated as a Slime   # season & platform breakdown
aninidhi airing                                           # list currently Airing dubs
aninidhi latest -n 5
aninidhi search Naruto
aninidhi info "Dan Da Dan"                                # per-platform breakdown for one title
aninidhi platform crunchyroll
aninidhi multi                                            # anime dubbed on 2+ platforms
aninidhi stats                                            # dub count per platform
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

