/**
 * ÖTKERT Commission Management App — Backend (Google Apps Script)
 *
 * This script must be bound to the Google Sheet that acts as the database
 * (Extensions > Apps Script from inside the Sheet). It exposes a small JSON
 * API (doGet / doPost) that the static HTML/JS frontend calls.
 *
 * One-time setup: run setupSheets() once from the Apps Script editor
 * (select it in the function dropdown and click Run) before deploying.
 */

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

var SHEET_DAILY = 'Daily_Data';
var SHEET_SETTINGS = 'Settings';
var SHEET_SUMMARY = 'Monthly_Summary';

var DAILY_HEADERS = ['ID', 'Dátum', 'Felhasznált kódok', 'Jutalék mérték', 'Jutalék', 'Létrehozva', 'Frissítve'];
var SETTINGS_HEADERS = ['Beállítás', 'Érték'];
var SUMMARY_HEADERS = ['Hónap', 'Felhasznált kódok', 'Jutalék'];

var SETTING_COMMISSION_PER_CODE = 'Jutalék kódonként';
var DEFAULT_COMMISSION_PER_CODE = 500;

var TIMEZONE = Session.getScriptTimeZone() || 'Europe/Budapest';

// ---------------------------------------------------------------------------
// One-time setup — run manually from the Apps Script editor
// ---------------------------------------------------------------------------

function setupSheets() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();

  var daily = getOrCreateSheet_(ss, SHEET_DAILY);
  ensureHeaders_(daily, DAILY_HEADERS);
  formatDailySheet_(daily);

  var settings = getOrCreateSheet_(ss, SHEET_SETTINGS);
  ensureHeaders_(settings, SETTINGS_HEADERS);
  if (settings.getLastRow() < 2) {
    settings.getRange(2, 1, 1, 2).setValues([[SETTING_COMMISSION_PER_CODE, DEFAULT_COMMISSION_PER_CODE]]);
  }
  formatSettingsSheet_(settings);

  var summary = getOrCreateSheet_(ss, SHEET_SUMMARY);
  ensureHeaders_(summary, SUMMARY_HEADERS);
  formatSummarySheet_(summary);
  rebuildMonthlySummarySheet_();

  // Remove the default empty "Sheet1" if it's still there and unused.
  var sheet1 = ss.getSheetByName('Sheet1');
  if (sheet1 && ss.getSheets().length > 1 && sheet1.getLastRow() === 0) {
    ss.deleteSheet(sheet1);
  }

  SpreadsheetApp.flush();
  Logger.log('Setup complete.');
}

function getOrCreateSheet_(ss, name) {
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  return sheet;
}

function ensureHeaders_(sheet, headers) {
  var range = sheet.getRange(1, 1, 1, headers.length);
  var existing = range.getValues()[0];
  var needsWrite = false;
  for (var i = 0; i < headers.length; i++) {
    if (existing[i] !== headers[i]) { needsWrite = true; break; }
  }
  if (needsWrite) range.setValues([headers]);
  sheet.setFrozenRows(1);
  range.setFontWeight('bold').setBackground('#1c1c1e').setFontColor('#ffffff');
}

function formatDailySheet_(sheet) {
  sheet.setColumnWidth(1, 60);   // ID
  sheet.setColumnWidth(2, 110);  // Date
  sheet.setColumnWidth(3, 100);  // Used Codes
  sheet.setColumnWidth(4, 130);  // Commission Rate
  sheet.setColumnWidth(5, 120);  // Commission
  sheet.setColumnWidth(6, 150);  // Created At
  sheet.setColumnWidth(7, 150);  // Updated At

  var maxRows = Math.max(sheet.getMaxRows(), 200);
  sheet.getRange(2, 2, maxRows - 1, 1).setNumberFormat('yyyy-mm-dd');
  sheet.getRange(2, 4, maxRows - 1, 2).setNumberFormat('#,##0 "HUF"');
  sheet.getRange(2, 6, maxRows - 1, 2).setNumberFormat('yyyy-mm-dd hh:mm:ss');

  applyFilter_(sheet, DAILY_HEADERS.length);
  protectSystemColumns_(sheet);
}

function formatSettingsSheet_(sheet) {
  sheet.setColumnWidth(1, 220);
  sheet.setColumnWidth(2, 140);
}

function formatSummarySheet_(sheet) {
  sheet.setColumnWidth(1, 140);
  sheet.setColumnWidth(2, 100);
  sheet.setColumnWidth(3, 140);
  var maxRows = Math.max(sheet.getMaxRows(), 50);
  sheet.getRange(2, 3, maxRows - 1, 1).setNumberFormat('#,##0 "HUF"');
}

function applyFilter_(sheet, numCols) {
  var existing = sheet.getFilter();
  if (existing) existing.remove();
  var lastRow = Math.max(sheet.getLastRow(), 1);
  sheet.getRange(1, 1, lastRow, numCols).createFilter();
}

function protectSystemColumns_(sheet) {
  // Best-effort: protect the ID/Commission Rate/Commission/timestamp columns
  // so people editing the sheet directly don't hand-edit generated values.
  // (Only takes effect for editors who aren't the sheet owner.)
  var protections = sheet.protections(SpreadsheetApp.ProtectionType.RANGE);
  for (var i = 0; i < protections.length; i++) protections[i].remove();
  ['A:A', 'D:D', 'E:E', 'F:F', 'G:G'].forEach(function (a1) {
    try {
      var range = sheet.getRange(a1);
      var protection = range.protect().setDescription('Rendszer által generált oszlop');
      protection.setWarningOnly(true);
    } catch (err) {
      // Protections can fail on brand-new sheets with no editors set; ignore.
    }
  });
}

// ---------------------------------------------------------------------------
// HTTP entry points
// ---------------------------------------------------------------------------

function doGet(e) {
  try {
    var action = e && e.parameter && e.parameter.action;
    var result;
    switch (action) {
      case 'getAll':
        result = getAllPayload_();
        break;
      case 'getData':
        result = { records: getDailyRecords_() };
        break;
      case 'getSettings':
        result = { settings: getSettingsPayload_() };
        break;
      case 'getSummary':
        result = { summary: computeSummary_(getDailyRecords_(), getCommissionRate_()) };
        break;
      default:
        return jsonResponse_({ success: false, error: 'Ismeretlen vagy hiányzó művelet.' });
    }
    return jsonResponse_({ success: true, data: result });
  } catch (err) {
    logError_('doGet', err);
    return jsonResponse_({ success: false, error: 'Hiba történt. Kérjük, próbálja újra.' });
  }
}

function doPost(e) {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(10000);
  } catch (err) {
    return jsonResponse_({ success: false, error: 'A rendszer elfoglalt, kérjük próbálja újra egy pillanat múlva.' });
  }

  try {
    var body = {};
    try {
      body = JSON.parse(e.postData.contents);
    } catch (parseErr) {
      return jsonResponse_({ success: false, error: 'Érvénytelen kérésformátum.' });
    }

    var action = body.action;
    var payload = body.payload || {};
    var result;

    switch (action) {
      case 'addRecord':
        result = addRecord_(payload);
        break;
      case 'updateRecord':
        result = updateRecord_(payload);
        break;
      case 'deleteRecord':
        result = deleteRecord_(payload);
        break;
      case 'updateSettings':
        result = updateSettings_(payload);
        break;
      default:
        return jsonResponse_({ success: false, error: 'Ismeretlen művelet.' });
    }

    if (result && result.error) {
      return jsonResponse_({ success: false, error: result.error });
    }

    return jsonResponse_({ success: true, data: getAllPayload_() });
  } catch (err) {
    logError_('doPost', err);
    return jsonResponse_({ success: false, error: 'Hiba történt. Kérjük, próbálja újra.' });
  } finally {
    lock.releaseLock();
  }
}

function jsonResponse_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function logError_(where, err) {
  Logger.log('[' + where + '] ' + (err && err.stack ? err.stack : err));
}

function getAllPayload_() {
  var records = getDailyRecords_();
  var rate = getCommissionRate_();
  return {
    records: records,
    settings: { commissionPerCode: rate },
    summary: computeSummary_(records, rate)
  };
}

// ---------------------------------------------------------------------------
// Daily_Data — read / write
// ---------------------------------------------------------------------------

function getDailySheet_() {
  return SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_DAILY);
}

function getDailyRecords_() {
  var sheet = getDailySheet_();
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return [];

  var values = sheet.getRange(2, 1, lastRow - 1, DAILY_HEADERS.length).getValues();
  var records = [];
  for (var i = 0; i < values.length; i++) {
    var row = values[i];
    if (row[0] === '' || row[0] === null) continue; // skip stray empty rows
    records.push({
      id: row[0],
      date: toIsoDate_(row[1]),
      usedCodes: Number(row[2]),
      commissionRate: Number(row[3]),
      commission: Number(row[4]),
      createdAt: toIsoDateTime_(row[5]),
      updatedAt: toIsoDateTime_(row[6]),
      _row: i + 2
    });
  }
  records.sort(function (a, b) { return b.date.localeCompare(a.date) || b.id - a.id; });
  records.forEach(function (r) { delete r._row; });
  return records;
}

function findRowById_(sheet, id) {
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return -1;
  var ids = sheet.getRange(2, 1, lastRow - 1, 1).getValues();
  for (var i = 0; i < ids.length; i++) {
    if (String(ids[i][0]) === String(id)) return i + 2;
  }
  return -1;
}

function nextId_(sheet) {
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return 1;
  var ids = sheet.getRange(2, 1, lastRow - 1, 1).getValues();
  var max = 0;
  for (var i = 0; i < ids.length; i++) {
    var n = Number(ids[i][0]);
    if (!isNaN(n) && n > max) max = n;
  }
  return max + 1;
}

function addRecord_(payload) {
  var validation = validateRecordInput_(payload);
  if (validation.error) return { error: validation.error };

  var sheet = getDailySheet_();
  var id = nextId_(sheet);
  var rate = getCommissionRate_();
  var commission = validation.usedCodes * rate;
  var now = new Date();

  sheet.appendRow([
    id,
    validation.dateObj,
    validation.usedCodes,
    rate,
    commission,
    now,
    now
  ]);

  rebuildMonthlySummarySheet_();
  return { id: id };
}

function updateRecord_(payload) {
  if (!payload || payload.id === undefined || payload.id === null || payload.id === '') {
    return { error: 'Hiányzó rögzítés-azonosító.' };
  }
  var validation = validateRecordInput_(payload);
  if (validation.error) return { error: validation.error };

  var sheet = getDailySheet_();
  var row = findRowById_(sheet, payload.id);
  if (row === -1) return { error: 'A rögzítés nem található.' };

  var rate = getCommissionRate_();
  var commission = validation.usedCodes * rate;
  var now = new Date();

  sheet.getRange(row, 2, 1, 6).setValues([[
    validation.dateObj,
    validation.usedCodes,
    rate,
    commission,
    sheet.getRange(row, 6).getValue(), // keep original Created At
    now
  ]]);

  rebuildMonthlySummarySheet_();
  return { id: payload.id };
}

function deleteRecord_(payload) {
  if (!payload || payload.id === undefined || payload.id === null || payload.id === '') {
    return { error: 'Hiányzó rögzítés-azonosító.' };
  }
  var sheet = getDailySheet_();
  var row = findRowById_(sheet, payload.id);
  if (row === -1) return { error: 'A rögzítés nem található.' };

  sheet.deleteRow(row);
  rebuildMonthlySummarySheet_();
  return { id: payload.id };
}

function validateRecordInput_(payload) {
  if (!payload) return { error: 'Hiányzó adat.' };

  var dateStr = payload.date;
  if (!dateStr || typeof dateStr !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
    return { error: 'Adjon meg egy érvényes dátumot (ÉÉÉÉ-HH-NN).' };
  }
  var dateObj = new Date(dateStr + 'T00:00:00');
  if (isNaN(dateObj.getTime())) {
    return { error: 'Adjon meg egy érvényes dátumot.' };
  }

  var usedCodesRaw = payload.usedCodes;
  var usedCodes = Number(usedCodesRaw);
  if (usedCodesRaw === '' || usedCodesRaw === null || usedCodesRaw === undefined ||
      isNaN(usedCodes) || !isFinite(usedCodes) ||
      Math.floor(usedCodes) !== usedCodes || usedCodes < 0) {
    return { error: 'A felhasznált kódok száma egész szám kell legyen, 0 vagy nagyobb.' };
  }

  return { dateObj: dateObj, usedCodes: usedCodes };
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

function getSettingsSheet_() {
  return SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_SETTINGS);
}

function getCommissionRate_() {
  var sheet = getSettingsSheet_();
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return DEFAULT_COMMISSION_PER_CODE;

  var values = sheet.getRange(2, 1, lastRow - 1, 2).getValues();
  for (var i = 0; i < values.length; i++) {
    if (values[i][0] === SETTING_COMMISSION_PER_CODE) {
      var v = Number(values[i][1]);
      return isNaN(v) ? DEFAULT_COMMISSION_PER_CODE : v;
    }
  }
  return DEFAULT_COMMISSION_PER_CODE;
}

function getSettingsPayload_() {
  return { commissionPerCode: getCommissionRate_() };
}

function updateSettings_(payload) {
  var rate = Number(payload && payload.commissionPerCode);
  if (isNaN(rate) || !isFinite(rate) || rate <= 0) {
    return { error: 'A kódonkénti jutaléknak pozitív számnak kell lennie.' };
  }

  var sheet = getSettingsSheet_();
  var lastRow = sheet.getLastRow();
  var rowIndex = -1;
  if (lastRow >= 2) {
    var values = sheet.getRange(2, 1, lastRow - 1, 1).getValues();
    for (var i = 0; i < values.length; i++) {
      if (values[i][0] === SETTING_COMMISSION_PER_CODE) { rowIndex = i + 2; break; }
    }
  }
  if (rowIndex === -1) {
    sheet.appendRow([SETTING_COMMISSION_PER_CODE, rate]);
  } else {
    sheet.getRange(rowIndex, 2).setValue(rate);
  }

  // Note: existing records keep the commission rate that was in effect when
  // they were saved (their own Commission Rate column is untouched), so
  // historical totals don't silently change. Only future records use the
  // new rate.
  return { commissionPerCode: rate };
}

// ---------------------------------------------------------------------------
// Summary (dashboard KPIs + monthly breakdown)
// ---------------------------------------------------------------------------

function computeSummary_(records, currentRate) {
  var totalCommission = 0;
  var totalCodes = 0;
  var thisMonthCommission = 0;
  var thisMonthCodes = 0;

  var now = new Date();
  var currentMonthKey = Utilities.formatDate(now, TIMEZONE, 'yyyy-MM');

  var monthlyMap = {}; // key: 'yyyy-MM' -> { codes, commission }

  for (var i = 0; i < records.length; i++) {
    var r = records[i];
    totalCommission += r.commission;
    totalCodes += r.usedCodes;

    var monthKey = r.date.substring(0, 7);
    if (!monthlyMap[monthKey]) monthlyMap[monthKey] = { codes: 0, commission: 0 };
    monthlyMap[monthKey].codes += r.usedCodes;
    monthlyMap[monthKey].commission += r.commission;

    if (monthKey === currentMonthKey) {
      thisMonthCommission += r.commission;
      thisMonthCodes += r.usedCodes;
    }
  }

  var monthly = Object.keys(monthlyMap).sort().map(function (key) {
    return {
      month: key,
      label: monthLabel_(key),
      usedCodes: monthlyMap[key].codes,
      commission: monthlyMap[key].commission
    };
  });

  return {
    totalCommission: totalCommission,
    totalCodes: totalCodes,
    thisMonthCommission: thisMonthCommission,
    thisMonthCodes: thisMonthCodes,
    currentRate: currentRate,
    monthly: monthly
  };
}

var HU_MONTHS_ = ['január', 'február', 'március', 'április', 'május', 'június',
  'július', 'augusztus', 'szeptember', 'október', 'november', 'december'];

function monthLabel_(key) {
  var parts = key.split('-');
  var monthIndex = Number(parts[1]) - 1;
  return parts[0] + '. ' + HU_MONTHS_[monthIndex];
}

function rebuildMonthlySummarySheet_() {
  var records = getDailyRecords_();
  var rate = getCommissionRate_();
  var summary = computeSummary_(records, rate);

  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_SUMMARY);
  var lastRow = sheet.getLastRow();
  if (lastRow > 1) {
    sheet.getRange(2, 1, lastRow - 1, SUMMARY_HEADERS.length).clearContent();
  }

  if (summary.monthly.length === 0) return;

  var rows = summary.monthly.map(function (m) {
    return [m.label, m.usedCodes, m.commission];
  });
  sheet.getRange(2, 1, rows.length, SUMMARY_HEADERS.length).setValues(rows);
}

// ---------------------------------------------------------------------------
// Date helpers
// ---------------------------------------------------------------------------

function toIsoDate_(value) {
  if (value instanceof Date) {
    return Utilities.formatDate(value, TIMEZONE, 'yyyy-MM-dd');
  }
  return String(value);
}

function toIsoDateTime_(value) {
  if (value instanceof Date) {
    return Utilities.formatDate(value, TIMEZONE, "yyyy-MM-dd'T'HH:mm:ss");
  }
  return String(value);
}
