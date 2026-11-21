import unittest
from datetime import date
import pandas as pd
from screener import (parse_stock_list, screen_stock, select_scan_date,
                      eligible_symbols, update_exclusions, split_download)


def sample_frame(last="2026-11-20", start=1000, step=2, volume=10_000_000,
                 range_fraction=0.08, count=65):
    dates = pd.bdate_range(end=last, periods=count)
    close = pd.Series([start + i * step for i in range(count)], index=dates, dtype=float)
    # Daily range 8% of close, and close stays between high and low.
    return pd.DataFrame({"Close": close, "High": close * (1 + range_fraction / 2),
                         "Low": close * (1 - range_fraction / 2),
                         "Volume": [volume] * count}, index=dates)


class ScreenerTests(unittest.TestCase):
    def scan(self, frame):
        return screen_stock(frame, frame.index[-1].strftime("%Y-%m-%d"))

    def test_stock_list_deduplicates(self):
        content = "Kode,Nama\nBBCA,BCA\nBBRI,BRI\nBBCA,Duplicate\nBBCA-W,Warrant\n"
        self.assertEqual(parse_stock_list(content), ["BBCA", "BBRI"])

    def test_passes_all_seven_rules(self):
        status, row = self.scan(sample_frame())
        self.assertEqual(status, "passed")
        self.assertGreaterEqual(row["value_ma5_idr"], 5_000_000_000)
        self.assertGreaterEqual(row["avg_range_5d_pct"], 5)
        self.assertLessEqual(row["price"], row["ma20"] * 1.05)

    def test_fails_low_value(self):
        self.assertEqual(self.scan(sample_frame(volume=1))[0], "failed")

    def test_fails_price_below_250(self):
        self.assertEqual(self.scan(sample_frame(start=100, step=1))[0], "failed")

    def test_fails_small_daily_range(self):
        self.assertEqual(self.scan(sample_frame(range_fraction=0.02))[0], "failed")

    def test_fails_more_than_five_pct_above_ma20(self):
        self.assertEqual(self.scan(sample_frame(step=20))[0], "failed")

    def test_fails_price_below_ema10(self):
        f = sample_frame()
        f.loc[f.index[-1], ["Close", "High", "Low"]] = [500, 520, 480]
        self.assertEqual(self.scan(f)[0], "failed")

    def test_rejects_missing_high_low(self):
        self.assertEqual(self.scan(sample_frame().drop(columns="High"))[0], "invalid")

    def test_rejects_bad_high_low(self):
        f = sample_frame()
        f.loc[f.index[-1], "Low"] = -1
        self.assertEqual(self.scan(f)[0], "invalid")

    def test_rejects_stale(self):
        self.assertEqual(screen_stock(sample_frame(), "2026-11-19")[0], "invalid")

    def test_rejects_short_history(self):
        self.assertEqual(self.scan(sample_frame(count=10))[0], "invalid")


class WorkflowFixTests(unittest.TestCase):
    def test_weekend_uses_friday(self):
        data = {"BBCA.JK": sample_frame(), "BBRI.JK": sample_frame()}
        self.assertEqual(select_scan_date(data, date(2026, 11, 21)), "2026-11-20")
        self.assertEqual(screen_stock(data["BBCA.JK"], "2026-11-20")[0], "passed")

    def test_reject_old_trading_dates(self):
        with self.assertRaises(ValueError):
            select_scan_date({"BBCA.JK": sample_frame("2026-11-06")}, date(2026, 11, 21))

    def test_choose_majority_date_not_one_new_ticker(self):
        data = {"A.JK": sample_frame(), "B.JK": sample_frame(),
                "C.JK": sample_frame("2026-11-21")}
        self.assertEqual(select_scan_date(data, date(2026, 11, 21)), "2026-11-20")

    def test_missing_twice_is_skipped_then_rechecked(self):
        symbol = "ARMY.JK"
        first = update_exclusions({}, [symbol], {}, [symbol], date(2026, 11, 21))
        self.assertEqual(first[symbol]["consecutive_failures"], 1)
        self.assertEqual(eligible_symbols([symbol], first, date(2026, 11, 22))[0], [symbol])
        second = update_exclusions(first, [symbol], {}, [symbol], date(2026, 11, 22))
        self.assertEqual(eligible_symbols([symbol], second, date(2026, 11, 23))[1], [symbol])
        self.assertEqual(eligible_symbols([symbol], second, date(2026, 12, 22))[0], [symbol])
        recovered = update_exclusions(second, [symbol], {symbol: sample_frame("2026-12-22")}, [], date(2026, 12, 22))
        self.assertNotIn(symbol, recovered)

    def test_batch_split(self):
        frame = sample_frame()
        combined = pd.concat({"BBCA.JK": frame, "BBRI.JK": frame}, axis=1)
        out = split_download(combined, ["BBCA.JK", "BBRI.JK", "LOST.JK"])
        self.assertEqual(sorted(out), ["BBCA.JK", "BBRI.JK"])
        self.assertIn("High", out["BBCA.JK"].columns)
        self.assertIn("Low", out["BBCA.JK"].columns)


if __name__ == "__main__":
    unittest.main()
