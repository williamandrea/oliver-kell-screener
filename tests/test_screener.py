import unittest
import pandas as pd
from screener import parse_stock_list, screen_stock


class ScreenerTests(unittest.TestCase):
    def test_stock_list_deduplicates(self):
        content = "Kode,Nama\nBBCA,BCA\nBBRI,BRI\nBBCA,Duplicate\nBBCA-W,Warrant\n"
        self.assertEqual(parse_stock_list(content), ["BBCA", "BBRI"])

    def test_passes_upward_price_and_volume(self):
        dates = pd.bdate_range("2026-08-03", periods=65)
        close = [1000 + x * 20 for x in range(65)]
        frame = pd.DataFrame({"Close": close, "Volume": [10_000_000] * 65}, index=dates)
        status, row = screen_stock(frame, dates[-1].strftime("%Y-%m-%d"))
        self.assertEqual(status, "passed")
        self.assertGreaterEqual(row["value_ma20_idr"], 5_000_000_000)

    def test_fails_low_value(self):
        dates = pd.bdate_range("2026-08-03", periods=65)
        frame = pd.DataFrame({"Close": [1000 + x * 20 for x in range(65)], "Volume": [1] * 65}, index=dates)
        self.assertEqual(screen_stock(frame, dates[-1].strftime("%Y-%m-%d"))[0], "failed")

    def test_rejects_stale(self):
        dates = pd.bdate_range("2026-08-03", periods=65)
        frame = pd.DataFrame({"Close": [1000] * 65, "Volume": [100] * 65}, index=dates)
        self.assertEqual(screen_stock(frame, "2026-11-20")[0], "invalid")

    def test_rejects_short_history(self):
        dates = pd.bdate_range("2026-11-02", periods=10)
        frame = pd.DataFrame({"Close": [1000] * 10, "Volume": [100] * 10}, index=dates)
        self.assertEqual(screen_stock(frame, dates[-1].strftime("%Y-%m-%d"))[0], "invalid")


if __name__ == "__main__":
    unittest.main()
