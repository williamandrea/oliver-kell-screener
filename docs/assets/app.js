"use strict";

const body = document.getElementById("stocks-body");
const notice = document.getElementById("notice");
const lastUpdate = document.getElementById("last-update");
const number = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const compact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });
const decimal = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
const validScanId = (value) => typeof value === "string" && /^\d{4}-\d{2}-\d{2}(?:-\d{4})?$/.test(value);

async function loadJSON(path) {
  const response = await fetch(path, { cache: "no-cache" });
  if (!response.ok) throw new Error(`Download failed: ${response.status}`);
  return response.json();
}

function showMessage(message) {
  notice.textContent = message;
  notice.hidden = !message;
}

function addCell(row, text, className = "") {
  const cell = document.createElement("td");
  cell.textContent = text;
  cell.className = className;
  row.append(cell);
}

function label(value, format = number, prefix = "", suffix = "") {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  return Number.isFinite(n) ? `${prefix}${format.format(n)}${suffix}` : "—";
}

function showStocks(stocks) {
  body.replaceChildren();
  if (!stocks.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 7;
    cell.className = "empty";
    cell.textContent = "No stocks passed all 7 rules.";
    row.append(cell);
    body.append(row);
    return;
  }
  for (const stock of stocks) {
    const row = document.createElement("tr");
    addCell(row, String(stock.ticker || "—"));
    addCell(row, label(stock.price), "right");
    addCell(row, label(stock.value_ma5_idr, compact, "Rp"), "right");
    addCell(row, label(stock.avg_range_5d_pct, decimal, "", "%"), "right");
    addCell(row, label(stock.ema10), "right");
    addCell(row, label(stock.ema20), "right");
    addCell(row, label(stock.ma20), "right");
    body.append(row);
  }
}

function scanTime(scan, scanId) {
  const time = scan.scanned_at || scan.summary?.scanned_at;
  if (typeof time === "string" && !Number.isNaN(Date.parse(time))) {
    return new Intl.DateTimeFormat("en-GB", {
      day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
      hour12: false, timeZone: "Asia/Jakarta"
    }).format(new Date(time)) + " WIB";
  }
  // Old daily scans have no recorded run time.
  const date = scan.date || scanId.slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return "Unknown";
  const formatted = new Intl.DateTimeFormat("en-GB", {
    day: "numeric", month: "short", year: "numeric", timeZone: "UTC"
  }).format(new Date(`${date}T00:00:00Z`));
  return scanId.length === 15 ? `${formatted}, ${scanId.slice(-4, -2)}:${scanId.slice(-2)} WIB` : `${formatted} (time unavailable)`;
}

async function start() {
  try {
    const manifest = await loadJSON("data/manifest.json");
    const scanId = manifest.latest;
    if (!validScanId(scanId)) {
      showStocks([]);
      lastUpdate.textContent = "Last update: No scans yet";
      showMessage("No published scan yet. Run GitHub Actions first.");
      return;
    }
    const scan = await loadJSON(`data/${scanId}.json`);
    if (!scan || !Array.isArray(scan.stocks) || !scan.summary || (scan.scan_id || scan.date) !== scanId) {
      throw new Error("Invalid scan data");
    }
    showStocks(scan.stocks);
    lastUpdate.textContent = `Last update: ${scanTime(scan, scanId)}`;
    if (scan.rules_version < 2) showMessage("This result uses older screening rules.");
  } catch (error) {
    console.error("Unable to show scan:", error);
    body.replaceChildren();
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 7;
    cell.className = "empty";
    cell.textContent = "Results unavailable.";
    row.append(cell);
    body.append(row);
    lastUpdate.textContent = "Last update: Unavailable";
    showMessage("Could not load the latest results. Check docs/data/manifest.json on GitHub.");
  }
}

start();
