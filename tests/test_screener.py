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

# Tests added after the first GitHub Actions run failed on a Saturday.
from datetime import date
from screener import select_scan_date, eligible_symbols, update_exclusions, split_download


class WorkflowFixTests(unittest.TestCase):
    def sample(self, last):
        dates = pd.bdate_range(end=last, periods=65)
        return pd.DataFrame({"Close": [1000 + i * 20 for i in range(65)],
                             "Volume": [10_000_000] * 65}, index=dates)

    def test_weekend_uses_friday(self):
        data = {"BBCA.JK": self.sample("2026-11-20"), "BBRI.JK": self.sample("2026-11-20")}
        self.assertEqual(select_scan_date(data, date(2026, 11, 21)), "2026-11-20")
        self.assertEqual(screen_stock(data["BBCA.JK"], "2026-11-20")[0], "passed")

    def test_reject_old_trading_dates(self):
        data = {"BBCA.JK": self.sample("2026-11-06")}
        with self.assertRaises(ValueError):
            select_scan_date(data, date(2026, 11, 21))

    def test_choose_majority_date_not_one_new_ticker(self):
        data = {"A.JK": self.sample("2026-11-20"), "B.JK": self.sample("2026-11-20"),
                "C.JK": self.sample("2026-11-21")}
        self.assertEqual(select_scan_date(data, date(2026, 11, 21)), "2026-11-20")

    def test_missing_twice_is_skipped_then_rechecked(self):
        symbol = "ARMY.JK"
        first = update_exclusions({}, [symbol], {}, [symbol], date(2026, 11, 21))
        self.assertEqual(first[symbol]["consecutive_failures"], 1)
        self.assertEqual(eligible_symbols([symbol], first, date(2026, 11, 22))[0], [symbol])
        second = update_exclusions(first, [symbol], {}, [symbol], date(2026, 11, 22))
        self.assertEqual(eligible_symbols([symbol], second, date(2026, 11, 23))[1], [symbol])
        self.assertEqual(eligible_symbols([symbol], second, date(2026, 12, 22))[0], [symbol])
        recovered = update_exclusions(second, [symbol], {symbol: self.sample("2026-12-22")}, [], date(2026, 12, 22))
        self.assertNotIn(symbol, recovered)

    def test_batch_split(self):
        frame = self.sample("2026-11-20")
        combined = pd.concat({"BBCA.JK": frame, "BBRI.JK": frame}, axis=1)
        out = split_download(combined, ["BBCA.JK", "BBRI.JK", "LOST.JK"])
        self.assertEqual(sorted(out), ["BBCA.JK", "BBRI.JK"])
