"""Daily IDX screener. Uses public stock list and Yahoo Finance daily data."""
from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

LOG = logging.getLogger("idx_screener")
ROOT = Path(__file__).resolve().parent
UNIVERSE_FILE = ROOT / "data" / "stocks.csv"
HISTORY = ROOT / "history"
# Public, community-maintained list. Never silently scan a short or stale fallback list.
STOCK_SOURCES = [
    "https://raw.githubusercontent.com/YusufCahyoNusantoro/idx-screener/main/daftar_saham.csv",
    "https://raw.githubusercontent.com/YusufCahyoNusantoro/idx-screener/master/daftar_saham.csv",
]
MIN_UNIVERSE = 700
BATCH_SIZE = 40
MIN_BARS = 45
VALUE_MIN = 5_000_000_000
LOCAL_TZ = ZoneInfo("Asia/Jakarta")


def parse_stock_list(content: str) -> list[str]:
    """Read a CSV with common Indonesian stock code header names."""
    text = content.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []
    headers = {name.strip().lower(): name for name in reader.fieldnames}
    key = next((headers[k] for k in ("kode", "kode saham", "kode_saham", "code", "ticker", "symbol", "stock code", "stock_code") if k in headers), None)
    if not key:
        LOG.warning("Unknown stock list headers: %s", reader.fieldnames)
        return []
    codes = set()
    for row in reader:
        code = str(row.get(key) or "").strip().upper().removesuffix(".JK")
        # Avoid warrants, funds or odd symbols.
        if re.fullmatch(r"[A-Z]{4}", code):
            codes.add(code)
    return sorted(codes)


def load_universe(refresh: bool = True, session: requests.Session | None = None) -> list[str]:
    cached = []
    if UNIVERSE_FILE.exists():
        cached = parse_stock_list(UNIVERSE_FILE.read_text(encoding="utf-8-sig"))
    if refresh:
        s = session or requests.Session()
        for url in STOCK_SOURCES:
            try:
                response = s.get(url, timeout=25, headers={"User-Agent": "idx-simple-screener/1.0"})
                response.raise_for_status()
                fresh = parse_stock_list(response.text)
                if len(fresh) < MIN_UNIVERSE:
                    raise ValueError(f"only {len(fresh)} valid stock codes")
                UNIVERSE_FILE.parent.mkdir(parents=True, exist_ok=True)
                UNIVERSE_FILE.write_text("code\n" + "\n".join(fresh) + "\n", encoding="utf-8")
                LOG.info("Updated stock list: %d codes", len(fresh))
                return fresh
            except (requests.RequestException, ValueError) as exc:
                LOG.warning("Stock list source unavailable: %s", exc)
    if len(cached) >= MIN_UNIVERSE:
        LOG.warning("Using saved stock list (%d codes).", len(cached))
        return cached
    raise RuntimeError("No full stock list available. Check stock list source and run again. No partial scan saved.")


def split_download(data: pd.DataFrame | None, symbols: list[str]) -> dict[str, pd.DataFrame]:
    if data is None or data.empty:
        return {}
    result = {}
    for symbol in symbols:
        try:
            frame = data[symbol] if isinstance(data.columns, pd.MultiIndex) else data
            frame = frame[["Close", "Volume"]].dropna(subset=["Close", "Volume"])
            if not frame.empty:
                result[symbol] = frame
        except (KeyError, TypeError):
            continue
    return result


def fetch_prices(symbols: list[str], batch_size: int = BATCH_SIZE) -> tuple[dict[str, pd.DataFrame], list[str]]:
    import yfinance as yf
    downloaded: dict[str, pd.DataFrame] = {}
    pending: list[str] = []
    for n in range(0, len(symbols), batch_size):
        batch = symbols[n:n + batch_size]
        try:
            data = yf.download(
                tickers=batch, period="3mo", interval="1d", group_by="ticker",
                auto_adjust=False, threads=4, progress=False, timeout=20,
            )
            downloaded.update(split_download(data, batch))
        except Exception as exc:
            LOG.warning("Batch %d failed: %s", n // batch_size + 1, exc)
        pending.extend(symbol for symbol in batch if symbol not in downloaded)
        LOG.info("Downloaded %d/%d stocks", len(downloaded), len(symbols))
        time.sleep(1)
    # Retry missing codes as smaller batches, but don't retry indefinitely.
    for n in range(0, len(pending), 5):
        batch = pending[n:n + 5]
        try:
            data = yf.download(tickers=batch, period="3mo", interval="1d", group_by="ticker",
                               auto_adjust=False, threads=False, progress=False, timeout=20)
            downloaded.update(split_download(data, batch))
        except Exception as exc:
            LOG.warning("Retry failed: %s", exc)
        time.sleep(2)
    missing = [symbol for symbol in symbols if symbol not in downloaded]
    return downloaded, missing


def screen_stock(frame: pd.DataFrame, scan_date: str) -> tuple[str, dict | None]:
    """Return status ('passed', 'failed', 'invalid') and row, if passed."""
    if len(frame) < MIN_BARS:
        return "invalid", None
    frame = frame.sort_index().copy()
    dates = pd.to_datetime(frame.index).strftime("%Y-%m-%d")
    if dates[-1] != scan_date:
        return "invalid", None
    close = pd.to_numeric(frame["Close"], errors="coerce")
    volume = pd.to_numeric(frame["Volume"], errors="coerce")
    if (close.isna().any() or volume.isna().any() or (close <= 0).any()
            or (volume < 0).any()):
        return "invalid", None
    ema10 = close.ewm(span=10, adjust=False).mean()
    ema20 = close.ewm(span=20, adjust=False).mean()
    value_ma20 = (close * volume).tail(20).mean()
    price = float(close.iloc[-1])
    current_ema10 = float(ema10.iloc[-1])
    current_ema20 = float(ema20.iloc[-1])
    old_ema20 = float(ema20.iloc[-6])  # 5 trading sessions ago
    passed = (price >= current_ema10 >= current_ema20 >= old_ema20
              and value_ma20 >= VALUE_MIN)
    if not passed:
        return "failed", None
    return "passed", {
        "ticker": "", "price": round(price, 2), "ema10": round(current_ema10, 2),
        "ema20": round(current_ema20, 2), "ema20_5d_ago": round(old_ema20, 2),
        "value_ma20_idr": round(float(value_ma20)),
    }


def save_results(date: str, rows: list[dict], missing: list[str], total: int, valid: int) -> None:
    HISTORY.mkdir(parents=True, exist_ok=True)
    with (HISTORY / f"{date}.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ticker", "price", "ema10", "ema20", "ema20_5d_ago", "value_ma20_idr"])
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: row["ticker"]))
    (HISTORY / f"{date}-missing.txt").write_text("\n".join(sorted(missing)) + ("\n" if missing else ""), encoding="utf-8")
    summary = {"date": date, "total_stocks": total, "valid_stocks": valid,
               "passed": len(rows), "missing_or_invalid": len(missing),
               "value_note": "Close times Yahoo volume: approximate daily traded value"}
    (HISTORY / f"{date}-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if rows:
        print("Matched: " + ", ".join(sorted(r["ticker"] for r in rows)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple daily IDX stock screener")
    parser.add_argument("--date", default=datetime.now(LOCAL_TZ).strftime("%Y-%m-%d"),
                        help="Expected last trading date YYYY-MM-DD (default: today Jakarta)")
    parser.add_argument("--no-refresh", action="store_true", help="Use saved stock list")
    parser.add_argument("--tickers", help="Test a few codes, e.g. BBCA,BBRI,TLKM (no full scan)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    datetime.strptime(args.date, "%Y-%m-%d")
    if args.tickers:
        codes = sorted({x.strip().upper().removesuffix(".JK") for x in args.tickers.split(",") if x.strip()})
        if any(not re.fullmatch(r"[A-Z]{4}", code) for code in codes):
            parser.error("Tickers must contain exactly 4 letters")
        # Test mode never writes misleading 'full market' history.
        persist = False
    else:
        codes = load_universe(refresh=not args.no_refresh)
        persist = True
    symbols = [code + ".JK" for code in codes]
    prices, failed = fetch_prices(symbols)
    invalid = list(failed)
    rows = []
    valid = 0
    for symbol, frame in prices.items():
        status, row = screen_stock(frame, args.date)
        if status == "invalid":
            invalid.append(symbol)
        else:
            valid += 1
            if row:
                row["ticker"] = symbol.removesuffix(".JK")
                rows.append(row)
    if valid == 0:
        raise SystemExit("No valid stock data for this date. No history saved (holiday, data delay, or source error).")
    if persist:
        save_results(args.date, rows, invalid, len(codes), valid)
    else:
        print(f"Test scan: {valid}/{len(codes)} valid; {len(rows)} passed; {len(invalid)} missing")
        for row in rows:
            print(row)


if __name__ == "__main__":
    main()
