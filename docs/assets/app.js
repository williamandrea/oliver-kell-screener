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

// Logo URLs only accept ordinary IDX stock codes, never arbitrary URLs.
function stockLogoUrl(ticker) {
  const symbol = String(ticker || "").toUpperCase();
  return /^[A-Z0-9]{3,6}$/.test(symbol)
    ? `https://assets.stockbit.com/logos/companies/${symbol}.png`
    : null;
}

function addStockCell(row, ticker) {
  const cell = document.createElement("td");
  const content = document.createElement("span");
  content.className = "stock-cell";
  const symbol = String(ticker || "—").replace(/\.JK$/i, "").toUpperCase();
  const url = stockLogoUrl(symbol);
  if (url) {
    const logo = document.createElement("img");
    logo.className = "stock-logo";
    logo.src = url;
    logo.alt = ""; // The stock code beside it already identifies the company.
    logo.width = 26;
    logo.height = 26;
    logo.loading = "lazy";
    logo.decoding = "async";
    logo.referrerPolicy = "no-referrer";
    logo.addEventListener("error", () => logo.remove(), { once: true });
    content.append(logo);
  }
  const code = document.createElement("span");
  code.textContent = symbol;
  content.append(code);
  cell.append(content);
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
    addStockCell(row, stock.ticker);
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

// A scan becomes late only after the next scheduled scan has had 90 minutes
// to finish. Weekends have no scheduled scans.
function latestDueScan(now) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Jakarta", year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", hourCycle: "h23", weekday: "short"
  }).formatToParts(now);
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  const day = `${values.year}-${values.month}-${values.day}`;
  const slots = values.weekday === "Fri" ? ["09:45", "14:45", "15:45", "18:45"]
    : ["Mon", "Tue", "Wed", "Thu"].includes(values.weekday)
      ? ["09:45", "13:45", "15:45", "18:45"] : [];
  // Asia/Jakarta is UTC+7 year-round. Allow 90 minutes for GitHub delays.
  for (const slot of slots.slice().reverse()) {
    const dueAt = new Date(`${day}T${slot}:00+07:00`);
    if (now.getTime() >= dueAt.getTime() + 90 * 60_000) return dueAt;
  }
  return null;
}

function scanTimestamp(scan, scanId) {
  if (typeof scan.scanned_at === "string" && scan.scanned_at.trim()) {
    const value = Date.parse(scan.scanned_at);
    if (Number.isFinite(value)) return value;
  }
  if (scanId.length === 15) {
    const clock = scanId.slice(11);
    const value = Date.parse(`${scanId.slice(0, 10)}T${clock.slice(0, 2)}:${clock.slice(2)}:00+07:00`);
    if (Number.isFinite(value)) return value;
  }
  // Old daily scans have no clock: treat them as end-of-day results.
  const value = Date.parse(`${scanId.slice(0, 10)}T23:59:59+07:00`);
  return Number.isFinite(value) ? value : NaN;
}

function warningMessages(scan, scanId, now = new Date()) {
  const warnings = [];
  const last = scanTimestamp(scan, scanId);
  const due = latestDueScan(now);
  if (!Number.isFinite(last) || now.getTime() - last > 7 * 86_400_000 ||
      (due && last < due.getTime())) {
    warnings.push("Latest results may be old. The most recent scheduled scan has not been published.");
  }
  const total = Number(scan.summary?.total_stocks);
  const missing = Number(scan.summary?.missing_or_invalid);
  if (Number.isInteger(total) && total > 0 && Number.isInteger(missing) &&
      missing >= 0 && missing / total >= 0.10) {
    warnings.push(`Incomplete scan: ${number.format(missing)} of ${number.format(total)} stocks (${decimal.format(missing / total * 100)}%) had missing or unusable data.`);
  }
  return warnings;
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
    const warnings = warningMessages(scan, scanId);
    if (scan.rules_version < 2) warnings.unshift("This result uses older screening rules.");
    showMessage(warnings.join(" "));
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
