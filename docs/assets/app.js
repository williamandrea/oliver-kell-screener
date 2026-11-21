"use strict";

const $ = (id) => document.getElementById(id);
const number = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const compact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });
const percent = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
const manifestPath = "data/manifest.json";
let allScans = [];
let selectedDate = null;

function friendlyDate(iso) {
  const parts = iso.split("-").map(Number);
  const date = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(date);
}

function shortDate(iso) {
  const date = new Date(`${iso}T00:00:00Z`);
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" }).format(date);
}

function setText(id, value) { $(id).textContent = value; }
function el(tag, className, textValue) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (textValue !== undefined) node.textContent = String(textValue);
  return node;
}
function showNotice(message) { $("notice").hidden = !message; $("notice").textContent = message || ""; }

async function getJSON(url) {
  const response = await fetch(url, { cache: "no-cache" });
  if (!response.ok) throw new Error(`Unable to load (${response.status})`);
  return response.json();
}

function renderSummary(scan) {
  const summary = scan.summary;
  setText("passed-count", number.format(summary.passed));
  setText("valid-count", number.format(summary.valid_stocks));
  setText("missing-count", number.format(summary.missing_or_invalid));
  const rate = summary.total_stocks ? summary.valid_stocks / summary.total_stocks * 100 : 0;
  const safeRate = Math.max(0, Math.min(100, rate));
  setText("coverage-percent", `${percent.format(safeRate)}%`);
  setText("coverage-caption", `${number.format(summary.valid_stocks)} of ${number.format(summary.total_stocks)} stocks had valid data`);
  $("coverage-fill").style.width = `${safeRate}%`;
  $("coverage-track").setAttribute("aria-valuenow", String(Math.round(safeRate)));
  setText("result-badge", `${scan.stocks.length} stocks`);
  setText("data-caption", scan.rules_version < 2 ? "Older results may use previous screening rules." : "Results use daily closing prices, not live prices.");
}

function renderStocks(stocks) {
  const body = $("stocks-body");
  body.replaceChildren();
  if (!stocks.length) {
    const row = el("tr");
    const cell = el("td", "empty-row", "No stocks passed on this trading day.");
    cell.colSpan = 6;
    row.append(cell);
    body.append(row);
    return;
  }
  for (const stock of stocks) {
    const row = el("tr");
    const first = el("td");
    const ticker = el("span", "stock-symbol");
    ticker.append(el("span", "stock-glyph", "↗"), el("span", "", stock.ticker));
    first.append(ticker);
    row.append(first);
    const fields = ["price", "value_ma5_idr", "avg_range_5d_pct", "ema10", "ema20"];
    for (const field of fields) {
      const value = Number(stock[field]);
      const valid = stock[field] !== undefined && Number.isFinite(value);
      let label = "—";
      if (valid) {
        label = field === "value_ma5_idr" ? `Rp${compact.format(value)}` :
          field === "avg_range_5d_pct" ? `${percent.format(value)}%` : number.format(value);
      }
      row.append(el("td", `right ${field === "avg_range_5d_pct" ? "positive-cell" : field === "price" ? "price-cell" : ""}`, label));
    }
    body.append(row);
  }
}

function renderHistory() {
  const history = $("history-list");
  history.replaceChildren();
  for (const item of allScans.slice(0, 6)) {
    const button = el("button", `history-button${selectedDate === item.date ? " active" : ""}`);
    button.type = "button";
    button.setAttribute("aria-label", `View ${friendlyDate(item.date)} scan, ${item.passed} stocks matched`);
    const left = el("span");
    left.append(el("span", "", friendlyDate(item.date)), el("small", "", `${number.format(item.valid)} valid stocks`));
    button.append(left, el("strong", "", String(item.passed)));
    button.addEventListener("click", () => selectDate(item.date));
    history.append(button);
  }
  const chart = $("history-bars");
  chart.replaceChildren();
  const lastSeven = allScans.slice(0, 7).reverse();
  if (!lastSeven.length) { chart.append(el("p", "muted", "No history yet.")); return; }
  const max = Math.max(1, ...lastSeven.map((item) => item.passed));
  for (const item of lastSeven) {
    const bar = el("div", `bar-item${item.date === selectedDate ? " selected" : ""}`);
    const barFill = el("div", "bar-fill");
    barFill.style.height = `${Math.max(3, Math.round(item.passed / max * 82))}%`;
    bar.append(el("span", "bar-count", String(item.passed)), barFill, el("span", "bar-label", shortDate(item.date)));
    bar.title = `${friendlyDate(item.date)}: ${item.passed} matched`;
    chart.append(bar);
  }
}

async function selectDate(day) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || !allScans.some((item) => item.date === day)) return;
  selectedDate = day;
  $("scan-date").value = day;
  renderHistory();
  showNotice("");
  try {
    const scan = await getJSON(`data/${day}.json`);
    if (selectedDate !== day) return;
    if (scan.date !== day || !Array.isArray(scan.stocks) || !scan.summary) throw new Error("Invalid scan data");
    renderSummary(scan);
    renderStocks(scan.stocks);
    if (scan.rules_version < 2) showNotice("This older scan used earlier screening rules. Compare results with care.");
  } catch (error) {
    if (selectedDate === day) {
      showNotice("Could not load this day's results. Please refresh and try again.");
      console.error("Scan data error:", error);
    }
  }
}

async function start() {
  try {
    const manifest = await getJSON(manifestPath);
    if (!Array.isArray(manifest.scans)) throw new Error("Invalid history list");
    allScans = manifest.scans.filter((item) => /^\d{4}-\d{2}-\d{2}$/.test(item.date));
    const picker = $("scan-date");
    picker.replaceChildren();
    if (!allScans.length) {
      picker.append(el("option", "", "No scans yet"));
      renderHistory();
      renderStocks([]);
      showNotice("No published scans yet. Run the GitHub Actions workflow to add the first results.");
      return;
    }
    for (const item of allScans) {
      const option = el("option", "", friendlyDate(item.date));
      option.value = item.date;
      picker.append(option);
    }
    picker.disabled = false;
    picker.addEventListener("change", (event) => selectDate(event.target.value));
    await selectDate(manifest.latest && allScans.some((item) => item.date === manifest.latest) ? manifest.latest : allScans[0].date);
  } catch (error) {
    showNotice("Could not load scan history. Please refresh or check the published site data.");
    setText("history-period", "Unavailable");
    console.error("Manifest error:", error);
  }
}
start();
