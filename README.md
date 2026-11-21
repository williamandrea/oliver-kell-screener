# Simple IDX Stock Screener

**For future AI agents:** Read `AGENTS.md` first. Update it after every project change.

Scans IDX stocks with free Yahoo Finance daily data. Saves daily matched stocks and scan status.

## Rules

A stock passes only when all seven rules are true:

1. Last close >= Rp250
2. Last close >= EMA 10
3. EMA 10 >= EMA 20
4. EMA 20 >= EMA 20 from 5 trading days earlier
5. Average (daily close * volume) over the last 5 trading days >= Rp5,000,000,000
6. Average daily range for 5 trading days >= 5%, where each day's range is `(High - Low) / Low * 100`
7. Last close <= 1.05 * MA 20 (simple average of the last 20 closes). A price below MA 20 is allowed.

**Note:** Rule 5 is an **estimate** of trading value, not actual exchange-recorded turnover. Yahoo volume and raw closing price are used.

## Start using GitHub (no server)

1. Make a **private** GitHub repository.
2. Upload all files from this ZIP, including the hidden `.github` folder.
3. In GitHub open **Settings -> Actions -> General**. Under **Workflow permissions**, allow read and write permissions. Save.
4. Open **Actions -> Daily IDX Scan -> Run workflow** to test the first scan.
5. Check **Actions** logs and the new files under `history/`. Daily runs are set for **18:37 Jakarta time, Monday-Friday**.

GitHub can delay or miss scheduled jobs. On a market holiday the scan should not save false history. If data is late or unavailable, results may be missing and will be listed.

## Results

Every successful full scan saves:

- `history/YYYY-MM-DD.csv`: stocks passing all seven rules
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

## Screening rule update (2026-11-21)

The screener now uses 7 rules. Output CSV columns: `ticker`, `price`, `ema10`, `ema20`, `ema20_5d_ago`, `value_ma5_idr`, `avg_range_5d_pct`, and `ma20`. The old `value_ma20_idr` output was replaced.

`High` and `Low` are required from Yahoo Finance. Stocks with missing or invalid fields are reported as invalid, not failed. The GitHub Actions schedule is unchanged.

## Stage 2: public dashboard (GitHub Pages)

The simple dark website lives in `docs/`. It shows the latest scan, passing stocks, and earlier scan dates. There is no search, CSV download, server, login, or third-party CSS/JavaScript service.

1. Keep running the existing **Daily IDX Scan** workflow; it now also runs `python build_site.py` and commits generated files under `docs/data/`.
2. Make the GitHub repository **Public** (Settings -> General -> Change repository visibility). **Warning:** all code and committed scan history become public. Check there are no secrets in the repository before changing visibility.
3. Go to **Settings -> Pages**. Under **Build and deployment**, choose **Deploy from a branch**, select **main** and **/docs**, then save.
4. Run **Actions -> Daily IDX Scan -> Run workflow** once to publish data. GitHub Pages then publishes the website. Find the URL in Settings -> Pages, normally `https://YOUR-USERNAME.github.io/YOUR-REPO/`.

If the site says *No published scans yet*, check that `docs/data/manifest.json` lists scan dates. You can also run `python build_site.py` locally to rebuild site data from saved `history/`. Old saved scans may use older screening rules, and the site marks them as such.

**Data safety:** the site only reads static JSON built from the CSV history. No API keys or private data are needed in the browser. The website uses no external scripts. GitHub Pages is public; don't store credentials in tracked files.
