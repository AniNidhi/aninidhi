"""Tests for aninidhi. Run with either:
    python -m unittest discover -s tests
    pytest
"""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))


class AninidhiTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["ANINIDHI_CACHE_DIR"] = self._tmp.name
        os.environ["ANINIDHI_SOURCE_URL"] = ""

        import importlib
        import aninidhi
        import aninidhi.data as data

        importlib.reload(data)
        importlib.reload(aninidhi)
        self.aninidhi = aninidhi

    def tearDown(self):
        self._tmp.cleanup()

    def test_list_all_returns_bundled_entries_offline(self):
        entries = self.aninidhi.list_all()
        self.assertGreater(len(entries), 400)
        self.assertIn("title", entries[0])
        self.assertIn("hindi_dubs", entries[0])

    def test_every_entry_has_at_least_one_dub(self):
        for a in self.aninidhi.list_all():
            self.assertTrue(a.get("hindi_available") or a.get("dubs"))
            self.assertGreaterEqual(len(a.get("hindi_dubs", []) or a.get("dubs", [])), 1)

    def test_get_latest_sorts_by_newest_dub_activity(self):
        latest = self.aninidhi.get_latest(limit=5)
        self.assertEqual(len(latest), 5)

        def newest(a):
            dubs = a.get("hindi_dubs") or a.get("dubs") or []
            return max(str(d["release_date"]) for d in dubs if d.get("release_date"))

        dates = [newest(a) for a in latest]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_get_upcoming_returns_list(self):
        upcoming = self.aninidhi.get_upcoming()
        self.assertIsInstance(upcoming, list)

    def test_search_is_case_insensitive(self):
        self.assertTrue(len(self.aninidhi.search("naruto")) >= 1)
        self.assertTrue(len(self.aninidhi.search("NARUTO")) >= 1)
        self.assertEqual(self.aninidhi.search("no such anime exists at all"), [])

    def test_get_by_platform_only_returns_matches_on_that_platform(self):
        results = self.aninidhi.get_by_platform("crunchyroll")
        self.assertGreater(len(results), 50)

    def test_get_by_language_returns_language_matches(self):
        results = self.aninidhi.get_by_language("Hindi")
        self.assertGreater(len(results), 400)

    def test_get_by_medium_returns_medium_matches(self):
        results = self.aninidhi.get_by_medium("OTT")
        self.assertGreater(len(results), 400)

    def test_get_dub_info_returns_full_breakdown(self):
        results = self.aninidhi.get_dub_info("Dan Da Dan")
        self.assertGreater(len(results), 0)

    def test_multi_platform_dubs_have_2_or_more_distinct_platforms(self):
        results = self.aninidhi.multi_platform_dubs()
        self.assertGreater(len(results), 10)

    def test_platform_stats_counts_match_get_by_platform(self):
        stats = self.aninidhi.platform_stats()
        self.assertIn("Crunchyroll", stats)

    def test_refresh_without_source_url_raises_clear_error(self):
        with self.assertRaises(RuntimeError):
            self.aninidhi.refresh()

    def test_data_source_reports_offline_mode_by_default(self):
        self.assertIn("bundled", self.aninidhi.data_source())


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["ANINIDHI_CACHE_DIR"] = self._tmp.name
        os.environ["ANINIDHI_SOURCE_URL"] = ""

        import importlib
        import aninidhi
        import aninidhi.cli
        import aninidhi.data as data

        importlib.reload(data)
        importlib.reload(aninidhi)
        importlib.reload(aninidhi.cli)

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, argv):
        from aninidhi.cli import main
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(argv)
        return code, buf.getvalue()

    def test_cli_latest_json_is_valid_json(self):
        code, out = self._run(["--json", "latest", "-n", "3"])
        self.assertEqual(code, 0)
        parsed = json.loads(out)
        self.assertLessEqual(len(parsed), 3)

    def test_cli_upcoming_command(self):
        code, out = self._run(["upcoming"])
        self.assertEqual(code, 0)

    def test_cli_search_table_output(self):
        code, out = self._run(["search", "one piece"])
        self.assertEqual(code, 0)
        self.assertIn("One Piece", out)

    def test_cli_language_command(self):
        code, out = self._run(["language", "Hindi"])
        self.assertEqual(code, 0)

    def test_cli_medium_command(self):
        code, out = self._run(["medium", "OTT"])
        self.assertEqual(code, 0)


class AutoSyncTests(unittest.TestCase):
    def test_auto_sync_helpers(self):
        from auto_sync import calculate_confidence, clean_anime_title, extract_release_date

        # YouTube Muse candidate
        c_youtube = {
            "source": "youtube:Muse_HindiDub",
            "video_title": "[Muse India] Solo Leveling Episode 01 (Hindi Dub)",
        }
        score, _ = calculate_confidence(c_youtube)
        self.assertGreaterEqual(score, 85)

        # Clean title
        cleaned = clean_anime_title("[AnimeMirchi] Bleach: Thousand-Year Blood War Hindi Dub Announced")
        self.assertEqual(cleaned, "Bleach: Thousand-Year Blood War")

        # Extract date
        dt, status = extract_release_date("Premieres on 2026-10-15")
        self.assertEqual(dt, "2026-10-15")

        # Extract TBA date
        dt_tba, status_tba = extract_release_date("Coming Soon schedule announced")
        self.assertEqual(dt_tba, "TBA")
        self.assertEqual(status_tba, "Upcoming")


class BumpVersionTests(unittest.TestCase):
    def test_bump_version_logic(self):
        from bump_version import bump_version_str
        self.assertEqual(bump_version_str("0.3.1", "patch"), "0.3.2")
        self.assertEqual(bump_version_str("0.3.1", "minor"), "0.4.0")
        self.assertEqual(bump_version_str("0.3.1", "major"), "1.0.0")


class InstagramScraperTests(unittest.TestCase):
    def test_target_accounts_loader(self):
        from fetch_instagram import load_target_accounts
        os.environ["INSTAGRAM_ACCOUNTS"] = "extra_user_one, extra_user_two"
        accounts = load_target_accounts(cli_accounts=["cli_user_three"])
        self.assertIn("cli_user_three", accounts)
        self.assertIn("extra_user_one", accounts)
        self.assertIn("extra_user_two", accounts)
        self.assertIn("crunchyrollin", accounts)

    def test_caption_phrase_detection(self):
        from fetch_instagram import clean_caption_title, detect_metadata_from_caption, is_meme_or_non_release

        caption_streaming_today = "🔥 Jujutsu Kaisen is streaming today in Hindi on Crunchyroll! #anime #jujutsukaisen"
        self.assertFalse(is_meme_or_non_release(caption_streaming_today, ["meme", "funny"]))
        meta = detect_metadata_from_caption(caption_streaming_today)
        self.assertEqual(meta["status"], "Airing")
        self.assertIn("Hindi", meta["languages"])
        clean_title = clean_caption_title(caption_streaming_today, "crunchyrollin")
        self.assertIn("Jujutsu Kaisen", clean_title)

        caption_weekly = "Demon Slayer Hindi dub streaming weekly every Sunday at 10 AM on Sony YAY!"
        meta_weekly = detect_metadata_from_caption(caption_weekly)
        self.assertEqual(meta_weekly["status"], "Airing")
        self.assertEqual(meta_weekly["medium"], "TV")

        caption_meme = "When your friend says anime is just cartoons 😂 #meme #funny"
        self.assertTrue(is_meme_or_non_release(caption_meme, ["meme", "funny"]))


class LeakPreventionTests(unittest.TestCase):
    def test_gitignore_contains_leak_prevention_rules(self):
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("*cookies*.txt", gitignore)
        self.assertIn(".env", gitignore)
        self.assertIn("*.session", gitignore)

    def test_manifest_contains_exclusion_rules(self):
        manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
        self.assertIn("exclude *cookies*.txt", manifest)
        self.assertIn("exclude .env*", manifest)
        self.assertIn("exclude *.session", manifest)


if __name__ == "__main__":
    unittest.main()
