# aninidhi

Track official **Hindi and regional Indian dubs** (Hindi, Tamil, Telugu, Malayalam, Bengali, Marathi, etc.) across Crunchyroll, Netflix, Muse India, Sony YAY!, Zee Cafe, Cartoon Network, Prime Video, and YouTube — as a Python library and CLI.

## What's new in v0.3.2

- **Self-Automated Release Sync (`auto_sync.py`)**: Automatic discovery and ingestion from YouTube, Anime Mirchi, Instagram, and RSS feeds with AniList metadata auto-enrichment.
- **Scheduled & TBA Dubs Tracker (`aninidhi upcoming` / `aninidhi.get_upcoming()`)**: Track scheduled announcements with both exact dates and TBA/Coming Soon dates.
- **Intelligent Confidence Scoring & Review Routing**: High-confidence announcements are auto-added into the dataset, while low-confidence items, multi-anime lineup posts, and edge cases are safely routed to `pending_review.json`.
- **Multi-Language & Regional Dubs**: Support for `language` queries (`Hindi`, `Tamil`, `Telugu`, `Malayalam`, `Bengali`, `Marathi`, etc.).
- **TV Channels & Broadcast Mediums**: Track TV channels (Sony YAY!, Cartoon Network, Zee Cafe, ETV Bal Bharat) alongside OTT platforms.
- **Series & Season Breakdown (`aninidhi series <title>`)**: Query a franchise name to see all available seasons, overall status, and per-platform/channel breakdown.
- **Airing Dubs Tracker (`aninidhi airing`)**: Quickly list anime currently airing dub episodes.
- **Python API & CLI Additions**: `aninidhi.get_upcoming()`, `aninidhi.get_by_language()`, `aninidhi.get_by_medium()`, CLI commands `aninidhi upcoming`, `aninidhi language <name>`, `aninidhi medium <name>`.

---

## Install

```bash
pip install aninidhi
```

---

## Developer Integrations & Use Cases

`aninidhi` is built specifically for developers to power anime apps, bots, and automation workflows. Here are common integration recipes:

### 1. Discord Bot Integration (`discord.py`)

Build a Discord bot command that responds to `/dub <anime>` or sends daily dub release alerts:

```python
import discord
from discord.ext import commands
import aninidhi

bot = commands.Bot(command_prefix="!")

@bot.command(name="dub")
async def dub_info(ctx, *, title: str):
    results = aninidhi.get_dub_info(title)
    if not results:
        await ctx.send(f"No official dub found for '{title}'.")
        return
    
    anime = results[0]
    dubs = anime.get("dubs") or anime.get("hindi_dubs") or []
    lines = [f"**{anime['title']}** [{anime.get('status', 'Finished')}]"]
    for d in dubs:
        lang = d.get("language", "Hindi")
        lines.append(f"• **{lang}**: {d['platform']} ({d.get('release_date', 'N/A')})")
    
    await ctx.send("\n".join(lines))
```

### 2. Telegram Bot Integration (`python-telegram-bot`)

Add regional anime dub search commands to your Telegram channel or group bot:

```python
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import aninidhi

async def search_dub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Usage: /dub <anime title>")
        return

    results = aninidhi.get_dub_info(query)
    if not results:
        await update.message.reply_text(f"No official dub found for '{query}'.")
        return

    anime = results[0]
    dubs = anime.get("dubs") or anime.get("hindi_dubs") or []
    lines = [f"🎬 *{anime['title']}* [{anime.get('status', 'Finished')}]"]
    for d in dubs:
        lang = d.get("language", "Hindi")
        lines.append(f"• *{lang}*: {d['platform']} ({d.get('release_date', 'N/A')})")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

app = ApplicationBuilder().token("YOUR_TELEGRAM_BOT_TOKEN").build()
app.add_handler(CommandHandler("dub", search_dub))
app.run_polling()
```

### 3. Lightweight Web API (FastAPI / Flask)

Expose a REST API to power web apps, mobile applications (Flutter/React Native), or dashboards:

```python
from fastapi import FastAPI
import aninidhi

app = FastAPI(title="Indian Anime Dub API")

@app.get("/api/latest")
def latest_dubs(limit: int = 10, language: str = None):
    return aninidhi.get_latest(limit=limit, language=language)

@app.get("/api/search")
def search_anime(q: str):
    return aninidhi.search(q)

@app.get("/api/language/{lang}")
def by_language(lang: str):
    return aninidhi.get_by_language(lang)
```

### 4. CLI & Shell Automation with `jq`

Use `aninidhi` in bash scripts or cron jobs to trigger webhooks or notifications when new dubs release:

```bash
# Get 5 latest releases in JSON and format with jq
aninidhi latest -n 5 --json | jq '.[] | {title: .title, dubs: .dubs}'

# Query dubs on TV channels
aninidhi medium TV --json
```

### 5. Data Analytics & Platform Stats

Track distribution trends across OTT platforms and Indian TV channels:

```python
import aninidhi

stats = aninidhi.platform_stats()
print("Top Dub Platforms & Channels:")
for platform, count in sorted(stats.items(), key=lambda kv: -kv[1]):
    print(f"  - {platform}: {count} dubs")
```

---

## Python SDK Reference

```python
import aninidhi

aninidhi.get_series_info("Slime")         # full franchise & season breakdown
aninidhi.get_airing()                     # all anime currently marked as Airing
aninidhi.get_upcoming()                   # all scheduled & TBA upcoming dubs
aninidhi.get_latest(limit=5)              # most recent dub activity
aninidhi.search("naruto")                 # title search
aninidhi.get_by_language("Hindi")         # anime dubbed in Hindi
aninidhi.get_by_language("Tamil")         # anime dubbed in Tamil
aninidhi.get_by_medium("TV")              # anime airing on TV channels (Sony YAY!, Zee Cafe, etc.)
aninidhi.get_by_platform("crunchyroll")   # anime on Crunchyroll
aninidhi.get_dub_info("Dan Da Dan")       # full per-platform breakdown for one title
aninidhi.multi_platform_dubs()            # anime dubbed on 2+ platforms
aninidhi.platform_stats()                 # {"Crunchyroll": 298, "Sony YAY!": 42, ...}
aninidhi.list_all()                       # complete dataset
```

Every function returns structured data shaped like this:

```json
{
  "id": 480,
  "title": "That Time I Got Reincarnated as a Slime (Season 4)",
  "status": "Airing",
  "season": 4,
  "hindi_available": true,
  "dubs": [
    { "language": "Hindi", "platform": "Crunchyroll", "medium": "OTT", "release_date": "2026-07-31", "status": "Finished", "media_type": "series" },
    { "language": "Hindi", "platform": "Sony YAY!", "medium": "TV", "release_date": "2026-06-02", "status": "Airing", "media_type": "series" },
    { "language": "Tamil", "platform": "Muse India", "medium": "YouTube", "release_date": "2026-08-29", "status": "Airing", "media_type": "series" }
  ]
}
```

---

## Command Line Usage

```bash
aninidhi series That Time I Got Reincarnated as a Slime   # season & platform breakdown
aninidhi airing                                           # list currently Airing dubs
aninidhi upcoming                                         # list scheduled & TBA upcoming dubs
aninidhi latest -n 5 -l Hindi                             # 5 latest Hindi dubs
aninidhi search Naruto
aninidhi language Tamil                                   # list Tamil dubs
aninidhi medium TV                                        # list TV channel dubs
aninidhi platform "Sony YAY!"
aninidhi multi                                            # anime dubbed on 2+ platforms
aninidhi stats                                            # dub count per platform/channel
aninidhi all --json
```

---

## Staying Fresh & Data Sync

`aninidhi` refreshes itself automatically once a day from the remote repository. If offline, it seamlessly falls back to cached data or local bundled snapshots so queries never fail.

To override or disable network checks:
```bash
export ANINIDHI_SOURCE_URL="https://raw.githubusercontent.com/you/your-fork/main/anime.json"
# or to disable network check completely:
export ANINIDHI_SOURCE_URL=""
```

Force an immediate refresh anytime with `aninidhi.refresh(force=True)` or `aninidhi refresh` on the CLI.

---

## License

MIT

