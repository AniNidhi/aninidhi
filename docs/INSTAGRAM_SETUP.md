# Instagram Dub Tracker Setup & Cookies Guide

This guide explains how to configure Instagram accounts and obtain session cookies for AniNidhi's automated dub discovery pipeline.

---

## 1. How to Obtain Instagram Cookies

Instagram requires a logged-in session to reliably poll account timelines without encountering login redirects or rate limits.

### Method 1: Export via Browser Extension (Recommended)

1. Open your browser (Chrome, Edge, Brave, or Firefox).
2. Log in to Instagram at [instagram.com](https://www.instagram.com). *(A secondary or backup account is recommended).*
3. Install the open-source extension:
   - **Chrome / Edge / Brave**: [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - **Firefox**: [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)
4. Navigate to `instagram.com` while logged in.
5. Click the extension icon and click **Export** to download the `instagram.com_cookies.txt` file in Netscape cookie format.
6. Rename or move the file to:
   ```
   config/instagram_cookies.txt
   ```
   *(This path is strictly ignored by `.gitignore` and can never be committed or leaked).*

### Method 2: Generate Session via Instaloader CLI

```bash
# In your virtual environment
pip install instaloader
instaloader --login YOUR_INSTAGRAM_USERNAME
```
Instaloader will log in (supporting 2FA) and store a local session file in `%LOCALAPPDATA%\Instaloader\session-YOUR_USERNAME` (Windows) or `~/.config/instaloader/session-YOUR_USERNAME` (Linux/macOS), which AniNidhi automatically detects.

### Method 3: GitHub Actions Automated Workflow (Cloud CI)

To enable Instagram scraping in GitHub Actions:
1. Go to your GitHub repository -> **Settings** -> **Secrets and variables** -> **Actions**.
2. Click **New repository secret**.
3. Name: `INSTAGRAM_COOKIES_FILE`.
4. Secret: Paste the entire text content of your `instagram_cookies.txt` file.
5. Save. The GitHub Actions workflow will automatically load the session for every auto-sync run.

---

## 2. How to Add Extra Instagram Usernames

You can configure target Instagram accounts using any of the following 3 ways:

### Option A: In `config/sources.json` (Project Configuration)
Edit [`config/sources.json`](file:///e:/Github%20Repository/Library/AniNidhi/AniNidhi/config/sources.json):
```json
{
  "instagram": {
    "target_accounts": [
      "crunchyrollin",
      "museindia",
      "sony_yay",
      "cartoonnetworkindia",
      "zeecafeindia",
      "etvbalbharat",
      "anime_mirchi",
      "netflix_in",
      "primevideoin",
      "your_custom_account"
    ]
  }
}
```

### Option B: Via Environment Variable (`INSTAGRAM_ACCOUNTS`)
Set `INSTAGRAM_ACCOUNTS` as a comma- or space-separated list:
```bash
# Windows PowerShell
$env:INSTAGRAM_ACCOUNTS="account1,account2,account3"

# Linux / macOS / Bash
export INSTAGRAM_ACCOUNTS="account1,account2,account3"
```

### Option C: Via CLI Flag
```bash
python scripts/fetch_instagram.py --accounts account1 account2 account3
```

---

## 3. Caption Parsing & Streaming Intent Detection

AniNidhi's caption analyzer automatically reads video and post captions for key streaming phrases:

| Caption Phrase Pattern | Detected Status | Action |
| :--- | :--- | :--- |
| `streaming today in hindi` | `Airing` | Auto-adds / updates entry as currently airing |
| `hindi dub streaming weekly` | `Airing` | Flags weekly broadcast schedule |
| `now streaming in hindi` | `Airing` | Records instant OTT availability |
| `episodes dropping every [day]` | `Airing` | Tracks ongoing episode release |
| `premieres on [date]` / `coming soon` | `Upcoming` | Tracks upcoming dub schedule |
| `watch now in [language]` | `Airing` | Detects multi-language dub support |

Memes, fan edits, cosplay, and AMVs are filtered out automatically using negative keyword filtering.
