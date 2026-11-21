# Simple IDX Stock Screener

**For future AI agents:** Read `AGENTS.md` first. Update it after every project change.

Scans IDX stocks with free Yahoo Finance daily data. Saves daily matched stocks and scan status.

## Rules

A stock passes only when all four rules are true:

1. Last close >= EMA 10
2. EMA 10 >= EMA 20
3. EMA 20 >= EMA 20 from 5 trading days earlier
4. Average (last 20 daily close * volume) >= Rp5,000,000,000

**Note:** Rule 4 is an **estimate** of trading value, not actual exchange-recorded turnover. Yahoo volume and raw closing price are used.

## Start using GitHub (no server)

1. Make a **private** GitHub repository.
2. Upload all files from this ZIP, including the hidden `.github` folder.
3. In GitHub open **Settings -> Actions -> General**. Under **Workflow permissions**, allow read and write permissions. Save.
4. Open **Actions -> Daily IDX Scan -> Run workflow** to test the first scan.
5. Check **Actions** logs and the new files under `history/`. Daily runs are set for **18:37 Jakarta time, Monday-Friday**.

GitHub can delay or miss scheduled jobs. On a market holiday the scan should not save false history. If data is late or unavailable, results may be missing and will be listed.

## Results

Every successful full scan saves:

- `history/YYYY-MM-DD.csv`: stocks passing all four rules
- `history/YYYY-MM-DD-summary.json`: number scanned, valid, passing, missing
- `history/YYYY-MM-DD-missing.txt`: stocks that failed or had unusable/stale data
- `data/stocks.csv`: the downloaded stock code list, kept as a backup

A failed full stock-list update uses the most recently saved list (if it has at least 700 stocks). On the very first run, an unavailable list will **stop** the scan rather than silently screen only a few stocks.

Stock list source: community-maintained public CSV at [YusufCahyoNusantoro/idx-screener](https://github.com/YusufCahyoNusantoro/idx-screener). The list URL/format may change. This source is **not** the official IDX feed; compare counts against the [IDX stock summary](https://www.idx.co.id/en/market-data/trading-summary/stock-summary). Yahoo may lack prices for some tickers.

## Run locally (optional)

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
python screener.py --tickers BBCA,BBRI,TLKM
python screener.py
```

A full scan downloads around 3 months for each stock in batches of 40. This first version **does not cache prices between GitHub runs** (the stock list and results are saved). If Yahoo rate-limits, try again later; we can add a price cache in a later update.

## Limits

- Personal research only; do not rely on results for trading decisions.
- Data may be late, incomplete or incorrect. IPOs with fewer than 45 daily price records are skipped.
- Yahoo Finance may restrict requests. No API key needed.
- GitHub Actions free usage and write permission depend on repository/account settings.
- Scheduled runs can fail. Check Actions logs regularly.
- This stage does not send Telegram messages or show a history website.

## Fixes after first live run (2026-11-21)

- Weekend/manual runs now use the latest common trading day found in Yahoo data (within the last 7 calendar days), not today's calendar date. Use `--date YYYY-MM-DD` to check a specific day.
- A missing Yahoo ticker is **not automatically called delisted**. After 2 failed daily downloads, it goes into `data/excluded_tickers.json` and is skipped for 30 days. It is then tried again. Recovered tickers are removed from the list.
- Temporarily skipped and missing tickers are shown in the daily missing report. An old or incomplete price history does **not** place a ticker on the skip list.
- Workflow uses Node.js 24-compatible `actions/checkout@v7` and `actions/setup-python@v7`.
- If there are no recent market dates or none of the stocks have valid prices, the scan still stops rather than saving false history.

To apply just the fix ZIP, extract it **over the existing project**, keeping its folders (especially `.github/workflows/`). Do not remove existing `history/` or `data/stocks.csv` files. Re-run **Actions > Daily IDX Scan > Run workflow** after committing the changes.
