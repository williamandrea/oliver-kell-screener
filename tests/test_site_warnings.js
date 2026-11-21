"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const context = vm.createContext({
  document: { getElementById: () => ({}) },
  Intl, Date, Number, String, Object, console: { error: () => {} },
  fetch: async () => { throw new Error("No network in test"); }
});
const source = fs.readFileSync(path.join(__dirname, "../docs/assets/app.js"), "utf8");
vm.runInContext(source.replace(/\s*start\(\);\s*$/, ""), context);
const warnings = (at, scannedAt, missing = 10, total = 900) =>
  Array.from(vm.runInContext(`warningMessages({scanned_at:${JSON.stringify(scannedAt)},summary:{missing_or_invalid:${missing},total_stocks:${total}}}, "2026-11-20-1845", new Date(${JSON.stringify(at)}))`, context));

// Saturday does not require a fresh scan; no false warning.
assert.deepEqual(warnings("2026-11-21T17:00:00+07:00", "2026-11-20T18:45:00+07:00"), []);
// Monday's morning scan gets 90 minutes after its scheduled time.
assert.deepEqual(warnings("2026-11-23T11:14:00+07:00", "2026-11-20T18:45:00+07:00"), []);
assert.match(warnings("2026-11-23T11:16:00+07:00", "2026-11-20T18:45:00+07:00")[0], /old/);
// On Fridays, the second scan is 14:45, not 13:45.
assert.deepEqual(warnings("2026-11-20T15:15:00+07:00", "2026-11-20T09:45:00+07:00"), []);
assert.match(warnings("2026-11-20T16:16:00+07:00", "2026-11-20T09:45:00+07:00")[0], /old/);
// Missing stocks: at least 10% triggers an easy-to-read warning.
assert.deepEqual(warnings("2026-11-21T17:00:00+07:00", "2026-11-20T18:45:00+07:00", 89), []);
assert.match(warnings("2026-11-21T17:00:00+07:00", "2026-11-20T18:45:00+07:00", 90)[0], /90 of 900/);
// Both warnings can appear together; future timestamps do not cause false stale warning.
assert.equal(warnings("2026-11-23T11:16:00+07:00", "2026-11-20T18:45:00+07:00", 100).length, 2);
assert.deepEqual(warnings("2026-11-20T18:45:00+07:00", "2026-11-20T18:46:00+07:00"), []);
// Only valid IDX symbols may be used for the external company logo.
assert.equal(vm.runInContext('stockLogoUrl("BRIS")', context), "https://assets.stockbit.com/logos/companies/BRIS.png");
assert.equal(vm.runInContext('stockLogoUrl("PKPK")', context), "https://assets.stockbit.com/logos/companies/PKPK.png");
assert.equal(vm.runInContext('stockLogoUrl("../wrong")', context), null);
assert.equal(vm.runInContext('stockLogoUrl("AAA?x=1")', context), null);
console.log("Website warning and logo tests passed (13 checks)");
