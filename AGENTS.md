# Project handoff for AI coding agents

Read this file before making changes. Update it after **every code or project change**, so the project can move to a new AI agent or Temporary Chat without losing context. Keep it accurate, short, and simple. Do not store secrets here.

## User preferences

- Reply with very short, plain, simple words. Avoid jargon.
- Before **large** changes, briefly describe the plan and wait for approval.
- Keep one project as the source of truth. Give updated files/ZIP, not full code pasted into chat.
- User prefers Temporary Chat and no saved chat history. Do not depend on chat history to resume.

## Goal

Build a free Python CLI stock screener for **all available IDX/IHSG-listed stocks** using Yahoo Finance data. Run it automatically using GitHub Actions; no local computer or paid server required. Future goals: Telegram alerts and a simple way to view past screener results.

## Screening rules (confirmed)

A stock passes only if **all four** pass, using daily data:

1. Latest daily close >= EMA(10).
2. EMA(10) >= EMA(20).
3. EMA(20) today >= EMA(20) from **5 trading sessions earlier**.
4. Mean of `daily close * daily volume` over the last **20 trading sessions** >= **IDR 5,000,000,000**.

Rule 4 is only a **trading value estimate**, not official traded value. Do not silently change the meaning.

## Confirmed decisions

- Cover the full available IDX stock list, not just LQ45.
- Refresh the stock list automatically, with a saved fallback list.
- Download market data in batches and retry failures.
- Skip and report stocks with missing, outdated, or unusable price data; do not assume they failed the rules.
- Run automatically on GitHub Actions on weekdays, after market close in Jakarta.
- Stage 1: daily scan + saved CSV history. Stage 2: Telegram notifications. Stage 3: history view.
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

**Current stage:** Stage 1 is running on GitHub, but the first full run failed; fixes are unit-tested but **not yet live-tested** on GitHub. Next: user uploads the fix files, commits, re-runs the workflow and shares any new error logs. The 4 screening rules remain unchanged. Daily price caching and Telegram are still future features.
