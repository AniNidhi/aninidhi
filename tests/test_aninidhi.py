"""Tests for aninidhi. Run with either:
    python -m unittest discover -s tests
    pytest
"""
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout


class AninidhiTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["ANINIDHI_CACHE_DIR"] = self._tmp.name
        os.environ.pop("ANINIDHI_SOURCE_URL", None)

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
            self.assertTrue(a["hindi_available"])
            self.assertGreaterEqual(len(a["hindi_dubs"]), 1)
            for d in a["hindi_dubs"]:
                self.assertIn("platform", d)
                self.assertIn("release_date", d)

    def test_get_latest_sorts_by_newest_dub_activity(self):
        latest = self.aninidhi.get_latest(limit=5)
        self.assertEqual(len(latest), 5)

        def newest(a):
            return max(d["release_date"] for d in a["hindi_dubs"])

        dates = [newest(a) for a in latest]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_search_is_case_insensitive(self):
        self.assertTrue(len(self.aninidhi.search("naruto")) >= 1)
        self.assertTrue(len(self.aninidhi.search("NARUTO")) >= 1)
        self.assertEqual(self.aninidhi.search("no such anime exists at all"), [])

    def test_get_by_platform_only_returns_matches_on_that_platform(self):
        results = self.aninidhi.get_by_platform("crunchyroll")
        self.assertGreater(len(results), 50)
        for a in results:
            platforms = {d["platform"].lower() for d in a["hindi_dubs"]}
            self.assertTrue(any("crunchyroll" in p for p in platforms))

    def test_get_dub_info_returns_full_breakdown(self):
        results = self.aninidhi.get_dub_info("Dan Da Dan")
        self.assertGreater(len(results), 0)
        for a in results:
            self.assertIn("hindi_dubs", a)

    def test_multi_platform_dubs_have_2_or_more_distinct_platforms(self):
        results = self.aninidhi.multi_platform_dubs()
        self.assertGreater(len(results), 10)
        for a in results:
            platforms = {d["platform"] for d in a["hindi_dubs"]}
            self.assertGreaterEqual(len(platforms), 2)

    def test_multi_platform_min_platforms_argument(self):
        at_least_3 = self.aninidhi.multi_platform_dubs(min_platforms=3)
        at_least_2 = self.aninidhi.multi_platform_dubs(min_platforms=2)
        self.assertLessEqual(len(at_least_3), len(at_least_2))

    def test_platform_stats_counts_match_get_by_platform(self):
        stats = self.aninidhi.platform_stats()
        self.assertIn("Crunchyroll", stats)
        cr_dub_count = sum(
            1
            for a in self.aninidhi.list_all()
            for d in a["hindi_dubs"]
            if d["platform"] == "Crunchyroll"
        )
        self.assertEqual(stats["Crunchyroll"], cr_dub_count)

    def test_refresh_without_source_url_raises_clear_error(self):
        with self.assertRaises(RuntimeError):
            self.aninidhi.refresh()

    def test_data_source_reports_offline_mode_by_default(self):
        self.assertIn("bundled", self.aninidhi.data_source())


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["ANINIDHI_CACHE_DIR"] = self._tmp.name
        os.environ.pop("ANINIDHI_SOURCE_URL", None)

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

    def test_cli_search_table_output(self):
        code, out = self._run(["search", "one piece"])
        self.assertEqual(code, 0)
        self.assertIn("One Piece", out)

    def test_cli_info_shows_per_platform_breakdown(self):
        code, out = self._run(["info", "Dan Da Dan"])
        self.assertEqual(code, 0)
        self.assertIn("Crunchyroll", out)

    def test_cli_stats_lists_platforms(self):
        code, out = self._run(["stats"])
        self.assertEqual(code, 0)
        self.assertIn("Crunchyroll", out)

    def test_cli_multi_only_shows_multi_platform_titles(self):
        code, out = self._run(["--json", "multi"])
        self.assertEqual(code, 0)
        parsed = json.loads(out)
        self.assertGreater(len(parsed), 0)
        for a in parsed:
            platforms = {d["platform"] for d in a["hindi_dubs"]}
            self.assertGreaterEqual(len(platforms), 2)

    def test_cli_refresh_without_url_fails_gracefully(self):
        code, out = self._run(["refresh"])
        self.assertEqual(code, 1)

    def test_cli_json_flag_works_before_and_after_subcommand(self):
        code_before, out_before = self._run(["--json", "all"])
        code_after, out_after = self._run(["all", "--json"])
        self.assertEqual(code_before, 0)
        self.assertEqual(code_after, 0)
        self.assertEqual(json.loads(out_before), json.loads(out_after))


if __name__ == "__main__":
    unittest.main()