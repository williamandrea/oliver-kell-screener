"""Turn saved screener CSV history into small JSON files for GitHub Pages."""

from __future__ import annotations

import csv
from datetime import date
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
HISTORY = ROOT / "history"
OUTPUT = ROOT / "docs" / "data"
DATE_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:-(\d{4}))?-summary\.json$")
FIELDS = ("ticker", "price", "ema10", "ema20", "ema20_5d_ago", "value_ma5_idr", "avg_range_5d_pct", "ma20")
NUMBER_FIELDS = FIELDS[1:]


def as_count(value: object) -> int:
    if isinstance(value, bool) or isinstance(value, (dict, list)):
        raise ValueError("Expected nonnegative count")
    count = int(value)
    if count < 0:
        raise ValueError("Negative count")
    return count


def parse_day(value: str) -> str:
    if date.fromisoformat(value).isoformat() != value:
        raise ValueError("Invalid day")
    return value


def read_scan(csv_path: Path, summary_path: Path, day: str, scan_id: str) -> dict:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("date") != day:
        raise ValueError("Summary date mismatch")
    totals = {key: as_count(summary[key]) for key in ("total_stocks", "valid_stocks", "passed", "missing_or_invalid")}
    if totals["valid_stocks"] > totals["total_stocks"]:
        raise ValueError("Invalid totals")
    stocks = []
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "ticker" not in reader.fieldnames:
            raise ValueError("Missing ticker field")
        for row in reader:
            symbol = (row.get("ticker") or "").strip().upper()
            if not re.fullmatch(r"[A-Z]{4}", symbol):
                raise ValueError(f"Invalid ticker: {symbol}")
            item = {"ticker": symbol}
            for field in NUMBER_FIELDS:
                raw = (row.get(field) or "").strip()
                if raw:
                    try:
                        numeric = float(raw)
                        if not (-1e15 < numeric < 1e15):
                            raise ValueError("Out-of-range number")
                        item[field] = numeric
                    except ValueError as exc:
                        raise ValueError(f"Invalid {field}: {symbol}") from exc
            stocks.append(item)
    if len(stocks) != totals["passed"]:
        raise ValueError("Passed count does not match CSV")
    stocks.sort(key=lambda row: row["ticker"])
    return {"date": day, "scan_id": scan_id, "scanned_at": summary.get("scanned_at", ""), "rules_version": as_count(summary.get("rules_version", 1)),
            "summary": {**totals, "temporarily_skipped": as_count(summary.get("temporarily_skipped", 0))},
            "stocks": stocks}


def build_site(history_dir: Path = HISTORY, output_dir: Path = OUTPUT) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    scans = []
    known = set()
    for path in sorted(history_dir.glob("*-summary.json")):
        match = DATE_FILE.fullmatch(path.name)
        if not match:
            continue
        day = parse_day(match.group(1))
        scan_id = path.name.removesuffix("-summary.json")
        if match.group(2) and (not match.group(2).isdigit() or int(match.group(2)[:2]) > 23 or int(match.group(2)[2:]) > 59):
            raise ValueError(f"Invalid scan time: {scan_id}")
        csv_path = history_dir / f"{scan_id}.csv"
        if not csv_path.is_file():
            raise ValueError(f"Missing CSV for {scan_id}")
        record = read_scan(csv_path, path, day, scan_id)
        (output_dir / f"{scan_id}.json").write_text(json.dumps(record, ensure_ascii=True, separators=(",", ":")) + "\n", encoding="utf-8")
        scans.append({"date": day, "scan_id": scan_id, "scanned_at": record["scanned_at"], "passed": record["summary"]["passed"],
                      "valid": record["summary"]["valid_stocks"],
                      "total": record["summary"]["total_stocks"],
                      "rules_version": record["rules_version"]})
        known.add(f"{scan_id}.json")
    # Remove old generated dates that no longer exist in the source history.
    for path in output_dir.glob("????-??-??*.json"):
        if path.name not in known:
            path.unlink()
    scans.sort(key=lambda item: (item["date"], item["scan_id"][11:] if len(item["scan_id"]) > 10 else "0000"), reverse=True)
    manifest = {"latest": scans[0]["scan_id"] if scans else None, "scans": scans}
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    manifest = build_site()
    print(f"Site data ready: {len(manifest['scans'])} days")
