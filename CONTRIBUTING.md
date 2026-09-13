# Contributing to aninidhi

## Project layout

- `src/aninidhi/` — the installable library and CLI.
- `src/aninidhi/data/anime.json` — the bundled dataset.
- `scripts/` — maintainer tooling, not shipped in the pip package.
- `.github/workflows/refresh-data.yml` — daily automation (see below).
- `tests/` — run with `python -m unittest discover -s tests`.

## Data provenance

The bundled dataset was compiled by cross-referencing each platform's own
release history (e.g. Crunchyroll's Simulcast Calendar). Snapshot date:
**September 2026**. It will go stale as new dubs release, which is what
the automation below and the enrichment scripts are for.

Sony YAY! and JioHotstar are known to carry Hindi-dubbed anime but aren't
in the dataset yet - their catalogs are more TV-schedule-based and harder
to date precisely from public sources. Good candidates for a future pass.

## Keeping the dataset current

`.github/workflows/refresh-data.yml` runs daily and:

1. Polls the Muse Hindi Dub YouTube channel for new uploads
   (`scripts/fetch_candidates.py`), queuing anything new into
   `pending_review.json`. Everything on that channel is Hindi-dubbed by
   definition, making it the highest-confidence automatable source.
2. Runs `scripts/flag_airing_review.py`, which lists every dub still
   marked `"Airing"` in `anime.json`. There's no free API that reports
   per-platform episode counts or completion status, so this step isn't
   fully automatic - it surfaces the list in the workflow log for a
   periodic manual glance.

**Setup**: get a free YouTube Data API v3 key at
[console.cloud.google.com](https://console.cloud.google.com), then add it
as a repo secret named `YOUTUBE_API_KEY` (Settings → Secrets and
variables → Actions).

**Workflow once candidates land in `pending_review.json`**:

1. Open the video, confirm it's a real episode (not a trailer).
2. Check `anime.json` for an existing entry to add a platform/date to, or
   create a new one.
3. Update `anime.json`, remove the handled entry from
   `pending_review.json`, commit and push.

Because `ANINIDHI_SOURCE_URL` defaults to this repo's `anime.json`,
pushing an update here reaches every installed copy of the library within
a day - no new PyPI release needed for data updates.

Test `fetch_candidates.py` manually (with `YOUTUBE_API_KEY` set locally)
before relying on the scheduled run.

## Enriching metadata (AniList + IMDb)

`genres`, `synopsis`, `studio`, `episodes`, and the AniList/IMDb ID+URL
fields ship as `null` on newly added entries. Two scripts fill them in,
one anime at a time, using each title as a search query:

```bash
# AniList - free, no API key needed
python scripts/enrich_anilist.py --limit 5   # try a handful first
python scripts/enrich_anilist.py

# IMDb ratings via OMDb (free key: https://www.omdbapi.com/apikey.aspx)
export OMDB_API_KEY=your_key_here
python scripts/enrich_imdb.py --limit 5
python scripts/enrich_imdb.py
```

Both do a plain title search, so expect occasional no-matches on titles
with cour/part splits - spot-check results before running either over the
full dataset.

## Running tests

```bash
pip install -e .
python -m unittest discover -s tests
```

All 18 tests run fully offline against the bundled dataset.