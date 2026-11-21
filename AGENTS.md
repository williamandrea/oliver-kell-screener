# Project handoff for AI coding agents

Read this file before making changes. Update it after **every code or project change**, so the project can move to a new AI agent or Temporary Chat without losing context. Keep it accurate, short, and simple. Do not store secrets here.

## User preferences

- Reply with very short, plain, simple words. Avoid jargon.
- Before **large** changes, briefly describe the plan and wait for approval.
- Keep one project as the source of truth. Give updated files/ZIP, not full code pasted into chat.
- User prefers Temporary Chat and no saved chat history. Do not depend on chat history to resume.

## Goal

Build a free Python CLI stock screener for **all available IDX/IHSG-listed stocks** using Yahoo Finance data. Run it automatically using GitHub Actions; no local computer or paid server required. Future goals: Telegram alerts and a simple way to view past screener results.

## Screening rules (confirmed, 7 rules)

A stock passes only if **all seven** pass using daily data:

1. Latest daily close >= IDR 250.
2. Latest daily close >= EMA(10).
3. EMA(10) >= EMA(20).
4. EMA(20) today >= EMA(20) from 5 trading sessions earlier.
5. Mean of `daily close * daily volume` over the last **5 trading sessions** >= IDR 5,000,000,000 (replaces previous 20-day rule).
6. Mean of `(daily high - daily low) / daily low * 100` over last 5 trading sessions >= 5%.
7. Latest daily close <= SMA(20) * 1.05. No requirement to be above SMA(20).

Trading value is an estimate, not the exchange's official reported turnover.

## Confirmed decisions

- Cover the full available IDX stock list, not just LQ45.
- Refresh the stock list automatically, with a saved fallback list.
- Download market data in batches and retry failures.
- Skip and report stocks with missing, outdated, or unusable price data; do not assume they failed the rules.
- Run automatically on GitHub Actions on weekdays, after market close in Jakarta.
- Stage 1: daily scan + saved CSV history. Stage 2: public static history website on GitHub Pages (now built). Telegram alerts are optional later.
- Private GitHub repository preferred. User must upload/push project files; the AI in this Temporary Chat cannot push directly.

## Current stage and status

**Stage 1 deployed to GitHub; first live run failed on Saturday 2026-11-21.** Data downloads worked for 919/962 stocks, but the program expected Saturday prices. The weekend-date and missing-ticker fixes passed 10 local tests. The updated version is not yet live verified.

Project files:

- `screener.py`: stock list loading, Yahoo downloads, indicator checks, output files.
- `.github/workflows/daily.yml`: weekday GitHub Actions schedule at 18:37 Asia/Jakarta, tests, scan, commit results.
- `tests/test_screener.py`: unit tests for ticker parsing, pass/fail, stale and short data.
- `requirements.txt`: Python packages.
- `README.md`: GitHub setup and CLI instructions.
- `data/stocks.csv`: saved stock list, created after successful full scan.
- `history/YYYY-MM-DD.csv`: matching stocks per scan.
- `history/YYYY-MM-DD-summary.json`: totals and missing-data summary.
- `history/YYYY-MM-DD-missing.txt`: missing/unusable stocks.

Current settings in `screener.py`: stock batches of 40, 3 months of daily prices, minimum 45 daily records, at least 700 stock codes to trust the stock list. Data is **not** yet cached between runs; only the stock list and scan results are saved.

## Known limits and things to check

- The stock list comes from a community-run GitHub CSV, **not** an official IDX list. Check list completeness/format and find a better source if needed.
- Yahoo Finance may delay data, miss stocks, limit requests, or change its API.
- Running after market close does not guarantee Yahoo has updated every ticker; stale tickers are reported.
- GitHub scheduled jobs may be delayed or skipped. Check logs.
- History files are committed by Actions; keep the token permission `contents: write`.
- On a market holiday, a run may use a recent prior trading day; if no recent or valid data exists, no history is saved.
- There is no live Yahoo end-to-end verification yet, and no Telegram or history web page yet.

## Next steps

1. User uploads/replaces the changed files from the fix ZIP in the existing GitHub repo, preserving paths.
2. User manually reruns GitHub Actions and checks saved history and missing reports.
3. Address any remaining live-data problems before adding Telegram.
4. Only then add Telegram, and later a history view, with user approval.

## Change log

- **2026-11-21 — Stage 1:** Created Python screener, weekday GitHub Actions workflow, tests, README, and saved-history format. Full market live run not verified.
- **2026-11-21 — Handoff file:** Added `AGENTS.md` and linked it from `README.md` so future AI agents can continue the work. No screening logic changed.

## Rule for future agents

For each project update: change code/docs as needed, run relevant tests, update the **Current stage**, **Known limits**, **Next steps**, and **Change log** in this file, and provide the updated project files/ZIP. Do not claim untested features work.

## Live scan findings and fixes (2026-11-21)

The first GitHub Actions manual run on Saturday 2026-11-21 loaded 962 symbols; Yahoo returned data for 919, while the scan failed because it required the last price date to equal Saturday. All original 5 tests passed. Yahoo gave no data for several symbols; this **does not prove delisting**. Node.js 20 deprecation warning came from `actions/checkout@v4` and `actions/setup-python@v5`.

Fixes in this update:
- Auto-select the most common recent stock trading date, within 7 calendar days, instead of assuming calendar today. `--date` still forces an expected date. Never save when no usable data.
- Track **Yahoo download failures only** in `data/excluded_tickers.json`. Once a symbol fails 2 runs in a row, skip it for 30 days, then check it again. Remove it if data returns. Skipped symbols stay in missing reports. These are unavailable symbols, not confirmed deleted stocks.
- Use `actions/checkout@v7` and `actions/setup-python@v7`, plus commit the exclusion file to GitHub.
- Added tests for weekend dates, stale data, mixed data dates, missing-ticker handling, and batch data format.

**Current stage:** Stage 1 is running on GitHub, but the first full run failed; fixes are unit-tested but **not yet live-tested** on GitHub. Next: user uploads the fix files, commits, re-runs the workflow and shares any new error logs. The screening rules were later expanded to 7 rules (see newest change log). Daily price caching and Telegram are still future features.

## Latest change (2026-11-21): expanded to 7 screening rules

- User approved 7 rules above. Value MA20 replaced by Value MA5; added price floor, average five-day daily range, and a 5% ceiling above simple MA20.
- `screener.py`: downloads Yahoo `High` and `Low` alongside `Close` and `Volume`; checks seven rules; writes new fields `value_ma5_idr`, `avg_range_5d_pct`, `ma20`. CSVs saved on future scans use the new format; old history is not rewritten.
- `tests/test_screener.py`: 16 local tests passed, including all new rules and missing OHLC data.
- `README.md`: updated rules and output format.
- `.github/workflows/daily.yml` unchanged. Current user report: GitHub workflow has already succeeded under the previous four-rule version. The seven-rule update is **not yet verified on GitHub**.
- **Next:** upload changed files preserving paths; run workflow manually and inspect `history/` CSV and summary; then discuss Telegram alerts.

## Latest change (2026-11-21): Stage 2 public static dashboard

User approved a dark, mobile-friendly website styled like the second design reference. **No search box and no CSV download buttons.** Public site approved. Code quality goals: simple, fast, safe, easy to maintain.

- Added `docs/index.html`, `docs/assets/styles.css`, `docs/assets/app.js`, `docs/assets/icon.svg`, and `docs/.nojekyll` for a plain static site without external JavaScript/CSS libraries or server.
- Added `build_site.py` to turn `history/YYYY-MM-DD.csv` and summary files into `docs/data/manifest.json` and per-date JSON. Data is checked before publishing. Site does not show invented sample stock results; no history means a clear empty state.
- Updated `.github/workflows/daily.yml` to build and commit website JSON after a successful scan. Daily scan schedule and seven screening rules are unchanged.
- Added `tests/test_build_site.py`. **21 local unit tests passed** (16 previous + 5 new). Full GitHub Pages deployment has not been verified.
- README explains how to set GitHub repo **Public** and enable Pages from `main` and `/docs`. Check for accidentally committed secrets before publishing the repo; all history becomes public.
- Website shows latest results, passing stocks, 7 rules, and history by day. It does **not** show Telegram alerts, offer search, or provide CSV download buttons.

**Next:** Apply the new/changed files to the GitHub repository, commit, set repository Public, enable Pages `main` `/docs`, run scan once, check deployed URL on desktop/mobile. If successful, consider Telegram alerts only if user wants them.

## Latest change (2026-11-21): 4 weekday scans and website diagnosis

- The user approved automatic runs at 09:45, 13:45, 15:45, 18:45 WIB Monday–Thursday; Friday second scan is 14:45 WIB. Same 7 rules.
- Yahoo officially lists **10-minute delayed quotes** for Indonesian `.JK` stocks; daily OHLCV may update at different times. Current-day bars are **unfinished** during trading and screening results can change by the final scan.
- `.github/workflows/daily.yml` runs four times weekdays with Asia/Jakarta timezone, invoking `screener.py --require-today` to avoid re-saving prior days on holidays/weekends. Delayed GitHub schedules may start late.
- `screener.py` saves each scan separately under `history/YYYY-MM-DD-HHMM.*` using actual Jakarta scan time. Old daily `history/YYYY-MM-DD.*` records remain supported. `--tickers BRIS,PKPK` prints failing rule names for debugging.
- `build_site.py` now produces one JSON per scan and a manifest sorted by scan time. `docs/assets/app.js` displays every scan time and can load both old daily and new time-stamped files. `docs/index.html` labels scan times and warns prices may be delayed.
- User's published website is https://williamandrea.github.io/oliver-kell-screener/. Its HTML was accessible, but live `docs/data/manifest.json` could **not** be read with available tools. Therefore, the exact reason BRIS and PKPK were missing was **not confirmed**. Possible reasons: published manifest is missing/stale or one or more stock rules failed. Never add these stocks to passing results without checking all 7 rules. After upload, verify site `data/manifest.json` and run `python screener.py --tickers BRIS,PKPK` locally.
- New local tests cover separate scan files and multiple scans per date. Next: upload changed files preserving folder paths, manually run one GitHub workflow, inspect output and confirm site displays a time and any matching stocks. If Yahoo daily bars do not update within the trading session, consider using Yahoo intraday bars to build today's candle.
