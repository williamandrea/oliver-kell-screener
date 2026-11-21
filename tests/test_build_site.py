"""Tests the public site's data build without any network access."""
import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from build_site import build_site


class SiteBuildTests(unittest.TestCase):
    def add_day(self, folder: Path, day: str, rows: list[dict], rules_version: int = 2):
        path = folder / f"{day}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["ticker", "price", "ema10", "ema20", "ema20_5d_ago", "value_ma5_idr", "avg_range_5d_pct", "ma20"])
            writer.writeheader()
            writer.writerows(rows)
        (folder / f"{day}-summary.json").write_text(json.dumps({"date": day, "total_stocks": 962, "valid_stocks": 900,
             "passed": len(rows), "missing_or_invalid": 62, "temporarily_skipped": 0, "rules_version": rules_version}), encoding="utf-8")

    def test_empty_history_builds_manifest(self):
        with TemporaryDirectory() as temporary:
            source, output = Path(temporary) / "history", Path(temporary) / "web"
            source.mkdir()
            self.assertEqual(build_site(source, output), {"latest": None, "scans": []})
            self.assertTrue((output / "manifest.json").exists())

    def test_multiple_days_sorted_and_numeric(self):
        with TemporaryDirectory() as temporary:
            source, output = Path(temporary) / "history", Path(temporary) / "web"
            source.mkdir()
            self.add_day(source, "2026-11-19", [{"ticker": "BBCA", "price": "9000", "avg_range_5d_pct": "5.25"}])
            self.add_day(source, "2026-11-20", [{"ticker": "BBRI", "price": "4800", "value_ma5_idr": "6000000000"}])
            manifest = build_site(source, output)
            self.assertEqual(manifest["latest"], "2026-11-20")
            self.assertEqual(len(manifest["scans"]), 2)
            content = json.loads((output / "2026-11-20.json").read_text())
            self.assertEqual(content["stocks"][0]["value_ma5_idr"], 6000000000)
            self.assertEqual(content["summary"]["valid_stocks"], 900)

    def test_refuse_bad_ticker(self):
        with TemporaryDirectory() as temporary:
            source, output = Path(temporary) / "history", Path(temporary) / "web"
            source.mkdir()
            self.add_day(source, "2026-11-20", [{"ticker": "BAD<script>", "price": "123"}])
            with self.assertRaises(ValueError):
                build_site(source, output)

    def test_refuse_incomplete_csv(self):
        with TemporaryDirectory() as temporary:
            source, output = Path(temporary) / "history", Path(temporary) / "web"
            source.mkdir()
            self.add_day(source, "2026-11-20", [{"ticker": "BBCA", "price": "100"}])
            (source / "2026-11-20.csv").write_text("ticker,price\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                build_site(source, output)

    def test_old_generated_days_removed(self):
        with TemporaryDirectory() as temporary:
            source, output = Path(temporary) / "history", Path(temporary) / "web"
            source.mkdir()
            output.mkdir()
            (output / "2020-01-01.json").write_text("{}", encoding="utf-8")
            build_site(source, output)
            self.assertFalse((output / "2020-01-01.json").exists())


if __name__ == "__main__":
    unittest.main()
