# Contributing to aninidhi

## Project layout

- `src/aninidhi/` — the installable library and CLI.
- `src/aninidhi/data/anime.json` — the bundled dataset.
- `scripts/` — maintainer tooling, not shipped in the pip package.
- `.github/workflows/refresh-data.yml` — daily automation (see below).
- `.github/workflows/data-recheck-reminder.yml` — monthly/quarterly
  reminder for platforms with no automatable feed (see below).
- `tests/` — run with `python -m unittest discover -s tests`.

## Data provenance

The bundled dataset was compiled by cross-referencing each platform's own
release history (e.g. Crunchyroll's Simulcast Calendar). Covers
Crunchyroll, Netflix, Muse India, Anime Times (Prime Video), and
JioHotstar. Snapshot date: **September 2026**. It will go stale as new
dubs release, which is what the automation below and `bulk_import.py`
are for.

**Sony YAY! isn't in the dataset yet.** Unlike the other platforms, it
has no single tracker page - its Hindi dub history is scattered across
many separate show-specific write-ups with month/year precision rather
than exact dates. Forcing it into a bulk import risked either fabricated
precision or messy partial data, so it's deferred to the manual recheck
process below instead, where it can be added show-by-show with real
dates as they're confirmed.

## Keeping the dataset current

### Daily automation

`.github/workflows/refresh-data.yml` runs daily and:

1. Polls three sources for new candidates (`scripts/fetch_candidates.py`),
   queuing anything new into `pending_review.json`:

   | Source | Setup | Reliability |
   |---|---|---|
   | Muse Hindi Dub YouTube (`@Muse_HindiDub`) | `YOUTUBE_API_KEY` secret | Frequently re-uploads dubs already released elsewhere - not a clean "new dub" signal |
   | Muse India main channel (`@MuseIndiaChannel`) | same key, filtered for "Hindi" in the title | Mixed-language channel, so filtering misses anything not explicitly labeled |
   | Crunchyroll News RSS | none needed, no key required | Global anime news filtered for "Hindi" - expect very few real matches |

   Every candidate is cross-checked against existing `anime.json` titles
   and labeled as a likely re-upload if a close match already exists -
   always verify this label rather than trusting it blindly.

   **Reddit's r/AnimeIndia is intentionally not included** - not pursuing
   it further.

2. Optionally polls any number of **Google Alerts** RSS feeds - set
   `GOOGLE_ALERTS_RSS_URLS` as a comma-separated list. Create each alert
   free at [google.com/alerts](https://google.com/alerts) with delivery
   set to "as-it-happens"; Google gives you an RSS URL per alert, zero
   code needed on our end. Since Netflix, Anime Times, and JioHotstar
   have no automatable feed of their own, alerts are the closest thing to
   automated coverage for them - worth creating one per platform:

   - `"hindi dub anime"` - general catch-all
   - `"hindi dub" netflix anime`
   - `"hindi dub" "prime video" OR "anime times"`
   - `"hindi dub" jiohotstar anime`

3. Runs `scripts/flag_airing_review.py`, which lists every dub still
   marked `"Airing"` in `anime.json` - no free API reports per-platform
   episode counts or completion status, so this stays a manual glance.

**Setup**: get a free YouTube Data API v3 key at
[console.cloud.google.com](https://console.cloud.google.com), add it as a
repo secret named `YOUTUBE_API_KEY`. Add `GOOGLE_ALERTS_RSS_URLS` as a
secret too, once you've created your alerts.

### Monthly/quarterly manual recheck

`.github/workflows/data-recheck-reminder.yml` runs on the 1st of every
month and opens a GitHub issue with a checklist for Netflix, Anime
Times, Sony YAY!, and JioHotstar - the platforms with no automatable
feed. Every 3rd occurrence (Jan/Apr/Jul/Oct) it's labeled as a quarterly
checkpoint, meant for a deeper pass than the usual monthly skim. This
doesn't do the research for you - it just makes sure the task doesn't
quietly get forgotten.

When you find something new, put it in a text file, one dub per line:

```
Title | Date | Status | Platform
Jujutsu Kaisen (Season 1) | Oct 09, 2025 | Finished | JioHotstar
```

Then run:

```bash
python scripts/bulk_import.py path/to/batch.txt
```

It matches against existing titles (merging into an existing anime's
`hindi_dubs` list when there's a match, creating a new entry when there
isn't) and re-sorts/renumbers `anime.json` automatically.

### Reviewing the daily queue, concretely

From your project root, with your virtual environment active:

```bash
python scripts/review_candidates.py
```

If `pending_review.json` is empty, either wait for the daily Action to
run, or populate it yourself right now with
`python scripts/fetch_candidates.py` (needs `YOUTUBE_API_KEY` set in your
shell first: `$env:YOUTUBE_API_KEY = "your-key"` in PowerShell).

For each candidate, the tool prints the video title, its URL, any
re-upload warning `fetch_candidates.py` already flagged, and any existing
`anime.json` titles that might match. **Open the URL in your browser
first** - the tool only has metadata, not the video content, so you need
to actually watch enough of it to confirm it's real. Then type one of:

| Type | What happens |
|---|---|
| `a` | Accept as a **brand new** anime entry - prompts for a clean title, platform, release date, status |
| `m` | Accept as a **new dub on an existing anime** - shows numbered matches, you pick one, then prompts for platform/date/status |
| `r` | **Reject** outright - removes it from the queue, nothing is added anywhere |
| `s` (or just Enter) | **Skip** for now - stays in the queue for next time |

The tool re-sorts and renumbers `anime.json` automatically after any
`a`/`m` change, but does **not** commit or push - review the diff
yourself (`git diff src/aninidhi/data/anime.json`), then `git add`,
`git commit`, `git push`.

### Removing an entry entirely

If something needs to come out of the dataset completely - added by
mistake, wrong match, anything that shouldn't be tracked - use:

```bash
python scripts/remove_entry.py "title or partial title"
```

It shows matches, asks which one and confirms before deleting, then
re-sorts/renumbers automatically. This is different from `[s]kip` in the
review tool, which only leaves a *pending candidate* in the queue for
later - this one deletes an entry already in `anime.json`.

Because `ANINIDHI_SOURCE_URL` defaults to this repo's `anime.json`, any
change pushed here (from review, bulk import, or removal) reaches every
installed copy of the library within a day - no new PyPI release needed.

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

All tests run fully offline against the bundled dataset.
