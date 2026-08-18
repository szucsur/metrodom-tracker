// ÖTKERT Commission Tracker — frontend logic
// Talks only to the Google Apps Script backend configured in config.js.
// No commission data is ever persisted in localStorage — Google Sheets is
// the single source of truth; every load re-fetches from the backend.

(function () {
  'use strict';

  var state = {
    records: [],
    settings: { commissionPerCode: 500 },
    summary: null,
    editingId: null,
    deleteTargetId: null,
    yearFilter: '',
    historySearch: '',
    historyMonthFilter: ''
  };

  var els = {}; // populated in init()

  // -------------------------------------------------------------------
  // API layer
  // -------------------------------------------------------------------

  function apiGet(action) {
    var url = CONFIG.API_URL + '?action=' + encodeURIComponent(action);
    return fetch(url).then(handleResponse);
  }

  function apiPost(action, payload) {
    return fetch(CONFIG.API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body: JSON.stringify({ action: action, payload: payload || {} })
    }).then(handleResponse);
  }

  function handleResponse(res) {
    if (!res.ok) throw new Error('Network error (' + res.status + ')');
    return res.json().then(function (body) {
      if (!body.success) throw new Error(body.error || 'Hiba történt. Kérjük, próbálja újra.');
      return body.data;
    });
  }

  function isConfigured() {
    return CONFIG.API_URL && CONFIG.API_URL.indexOf('ILLESSZE_BE') === -1;
  }

  // -------------------------------------------------------------------
  // Init
  // -------------------------------------------------------------------

  document.addEventListener('DOMContentLoaded', init);

  function init() {
    cacheEls();
    bindEvents();
    setDefaultDate();

    if (!isConfigured()) {
      showBanner('Az alkalmazás még nincs csatlakoztatva. Illessze be az Apps Script webalkalmazás URL-jét a config.js fájlba.');
      return;
    }

    loadAll(true);
  }

  function cacheEls() {
    els.banner = document.getElementById('banner');
    els.views = document.querySelectorAll('.view');
    els.navButtons = document.querySelectorAll('[data-view]');

    els.kpiTotalCommission = document.getElementById('kpi-total-commission');
    els.kpiMonthCommission = document.getElementById('kpi-month-commission');
    els.kpiTotalCodes = document.getElementById('kpi-total-codes');
    els.kpiMonthCodes = document.getElementById('kpi-month-codes');

    els.yearFilter = document.getElementById('year-filter');
    els.chart = document.getElementById('monthly-chart');
    els.monthlyTableBody = document.querySelector('#monthly-table tbody');
    els.monthlyEmpty = document.getElementById('monthly-empty');
    els.monthlyTableWrap = document.getElementById('monthly-table-wrap');

    els.form = document.getElementById('record-form');
    els.recordId = document.getElementById('record-id');
    els.fieldDate = document.getElementById('field-date');
    els.fieldCodes = document.getElementById('field-codes');
    els.errorDate = document.getElementById('error-date');
    els.errorCodes = document.getElementById('error-codes');
    els.commissionPreviewValue = document.getElementById('commission-preview-value');
    els.commissionPreviewHint = document.getElementById('commission-preview-hint');
    els.addFormTitle = document.getElementById('add-form-title');
    els.btnSaveRecord = document.getElementById('btn-save-record');
    els.btnCancelEdit = document.getElementById('btn-cancel-edit');

    els.historySearch = document.getElementById('history-search');
    els.historyMonthFilter = document.getElementById('history-month-filter');
    els.historyEmpty = document.getElementById('history-empty');
    els.historyNoResults = document.getElementById('history-no-results');
    els.btnAddFirst = document.getElementById('btn-add-first');
    els.historyTableBody = document.getElementById('history-table-body');
    els.historyCards = document.getElementById('history-cards');
    els.historyTableWrap = document.querySelector('.table-wrap.desktop-only');

    els.settingsForm = document.getElementById('settings-form');
    els.settingsCurrentRate = document.getElementById('settings-current-rate');
    els.fieldRate = document.getElementById('field-rate');
    els.errorRate = document.getElementById('error-rate');
    els.btnSaveSettings = document.getElementById('btn-save-settings');

    els.confirmModal = document.getElementById('confirm-modal');
    els.confirmOk = document.getElementById('confirm-ok');
    els.confirmCancel = document.getElementById('confirm-cancel');

    els.toastContainer = document.getElementById('toast-container');
    els.loadingOverlay = document.getElementById('loading-overlay');
    els.loadingText = document.getElementById('loading-text');
  }

  function bindEvents() {
    els.navButtons.forEach(function (btn) {
      btn.addEventListener('click', function () { switchView(btn.dataset.view); });
    });

    els.fieldDate.addEventListener('input', updateCommissionPreview);
    els.fieldCodes.addEventListener('input', updateCommissionPreview);
    els.form.addEventListener('submit', onSubmitRecord);
    els.btnCancelEdit.addEventListener('click', exitEditMode);

    els.yearFilter.addEventListener('change', function () {
      state.yearFilter = els.yearFilter.value;
      renderMonthly();
    });

    els.historySearch.addEventListener('input', function () {
      state.historySearch = els.historySearch.value.trim().toLowerCase();
      renderHistory();
    });
    els.historyMonthFilter.addEventListener('change', function () {
      state.historyMonthFilter = els.historyMonthFilter.value;
      renderHistory();
    });
    els.btnAddFirst.addEventListener('click', function () { switchView('add'); });

    els.settingsForm.addEventListener('submit', onSubmitSettings);

    els.confirmCancel.addEventListener('click', closeConfirmModal);
    els.confirmOk.addEventListener('click', onConfirmDelete);
  }

  function setDefaultDate() {
    var today = new Date();
    els.fieldDate.value = toIsoDate(today);
    updateCommissionPreview();
  }

  // -------------------------------------------------------------------
  // Navigation
  // -------------------------------------------------------------------

  function switchView(view) {
    els.views.forEach(function (v) { v.classList.toggle('active', v.id === 'view-' + view); });
    els.navButtons.forEach(function (btn) { btn.classList.toggle('active', btn.dataset.view === view); });
    if (view !== 'add' && state.editingId !== null) exitEditMode();
    window.scrollTo(0, 0);
  }

  // -------------------------------------------------------------------
  // Data loading
  // -------------------------------------------------------------------

  function loadAll(isInitial) {
    setLoading(true, isInitial ? 'Betöltés…' : 'Frissítés…');
    return apiGet('getAll')
      .then(function (data) {
        state.records = data.records || [];
        state.settings = data.settings || { commissionPerCode: 500 };
        state.summary = data.summary || null;
        hideBanner();
        renderAll();
      })
      .catch(function (err) {
        showBanner(friendlyError(err));
      })
      .finally(function () { setLoading(false); });
  }

  function renderAll() {
    renderKpis();
    renderMonthly();
    renderHistory();
    renderSettings();
    updateCommissionPreview();
  }

  // -------------------------------------------------------------------
  // Dashboard
  // -------------------------------------------------------------------

  function renderKpis() {
    var s = state.summary;
    if (!s) return;
    els.kpiTotalCommission.textContent = formatHuf(s.totalCommission);
    els.kpiMonthCommission.textContent = formatHuf(s.thisMonthCommission);
    els.kpiTotalCodes.textContent = formatNumber(s.totalCodes);
    els.kpiMonthCodes.textContent = formatNumber(s.thisMonthCodes);
  }

  function renderMonthly() {
    var s = state.summary;
    var monthly = (s && s.monthly) || [];

    // Year filter options
    var years = uniqueSorted(monthly.map(function (m) { return m.month.substring(0, 4); }));
    var currentYearValue = els.yearFilter.value || state.yearFilter;
    els.yearFilter.innerHTML = '<option value="">Minden év</option>' +
      years.map(function (y) { return '<option value="' + y + '">' + y + '</option>'; }).join('');
    els.yearFilter.value = years.indexOf(currentYearValue) !== -1 ? currentYearValue : '';
    state.yearFilter = els.yearFilter.value;

    var filtered = state.yearFilter
      ? monthly.filter(function (m) { return m.month.substring(0, 4) === state.yearFilter; })
      : monthly;

    var hasData = filtered.length > 0;
    els.monthlyEmpty.hidden = hasData;
    els.monthlyTableWrap.hidden = !hasData;
    els.chart.hidden = !hasData;

    if (!hasData) {
      els.chart.innerHTML = '';
      els.monthlyTableBody.innerHTML = '';
      return;
    }

    var maxCommission = Math.max.apply(null, filtered.map(function (m) { return m.commission; })) || 1;
    els.chart.innerHTML = filtered.map(function (m) {
      var heightPct = Math.max(4, Math.round((m.commission / maxCommission) * 100));
      return '<div class="chart-bar-wrap" title="' + m.label + ': ' + formatHuf(m.commission) + '">' +
        '<div class="chart-bar" style="height:' + heightPct + '%"></div>' +
        '<span class="chart-bar-label">' + shortMonthLabel(m.label) + '</span>' +
        '</div>';
    }).join('');

    els.monthlyTableBody.innerHTML = filtered.map(function (m) {
      return '<tr><td>' + escapeHtml(m.label) + '</td>' +
        '<td class="num">' + formatNumber(m.usedCodes) + '</td>' +
        '<td class="num">' + formatHuf(m.commission) + '</td></tr>';
    }).join('');
  }

  // -------------------------------------------------------------------
  // Add / Edit record
  // -------------------------------------------------------------------

  function updateCommissionPreview() {
    var codes = Number(els.fieldCodes.value);
    var rate = state.settings.commissionPerCode || 500;
    var valid = els.fieldCodes.value !== '' && !isNaN(codes) && codes >= 0 && Number.isInteger(codes);
    var commission = valid ? codes * rate : 0;
    els.commissionPreviewValue.textContent = formatHuf(commission);
    els.commissionPreviewHint.textContent = (valid ? codes : 0) + ' kód × ' + formatHuf(rate) + ' / kód';
  }

  function validateRecordForm() {
    var ok = true;
    els.errorDate.textContent = '';
    els.errorCodes.textContent = '';

    if (!els.fieldDate.value) {
      els.errorDate.textContent = 'Válasszon dátumot.';
      ok = false;
    }

    var codesRaw = els.fieldCodes.value;
    var codes = Number(codesRaw);
    if (codesRaw === '' || isNaN(codes) || !Number.isInteger(codes) || codes < 0) {
      els.errorCodes.textContent = 'Adjon meg egy egész számot, 0 vagy nagyobb.';
      ok = false;
    }

    return ok;
  }

  function onSubmitRecord(e) {
    e.preventDefault();
    if (!validateRecordForm()) return;

    var payload = {
      date: els.fieldDate.value,
      usedCodes: Number(els.fieldCodes.value)
    };

    var isEdit = state.editingId !== null;
    setButtonBusy(els.btnSaveRecord, true, isEdit ? 'Frissítés…' : 'Mentés…');

    var request = isEdit
      ? apiPost('updateRecord', Object.assign({ id: state.editingId }, payload))
      : apiPost('addRecord', payload);

    request
      .then(function (data) {
        state.records = data.records || [];
        state.settings = data.settings || state.settings;
        state.summary = data.summary || state.summary;
        renderAll();
        showToast(isEdit ? 'Rögzítés frissítve.' : 'Rögzítés mentve.', 'success');
        exitEditMode();
        switchView('history');
      })
      .catch(function (err) { showToast(friendlyError(err), 'error'); })
      .finally(function () { setButtonBusy(els.btnSaveRecord, false, isEdit ? 'Rögzítés frissítése' : 'Rögzítés mentése'); });
  }

  function enterEditMode(record) {
    state.editingId = record.id;
    els.recordId.value = record.id;
    els.fieldDate.value = record.date;
    els.fieldCodes.value = record.usedCodes;
    els.addFormTitle.textContent = 'Rögzítés szerkesztése';
    els.btnSaveRecord.textContent = 'Rögzítés frissítése';
    els.btnCancelEdit.hidden = false;
    updateCommissionPreview();
    switchView('add');
  }

  function exitEditMode() {
    state.editingId = null;
    els.recordId.value = '';
    els.addFormTitle.textContent = 'Napi rögzítés hozzáadása';
    els.btnSaveRecord.textContent = 'Rögzítés mentése';
    els.btnCancelEdit.hidden = true;
    setDefaultDate();
  }

  // -------------------------------------------------------------------
  // History
  // -------------------------------------------------------------------

  function renderHistory() {
    var records = state.records.slice(); // already sorted newest-first by backend

    // Month filter dropdown options
    var months = uniqueSorted(records.map(function (r) { return r.date.substring(0, 7); })).reverse();
    var currentMonthValue = els.historyMonthFilter.value || state.historyMonthFilter;
    els.historyMonthFilter.innerHTML = '<option value="">Minden hónap</option>' +
      months.map(function (m) { return '<option value="' + m + '">' + monthLabelFromKey(m) + '</option>'; }).join('');
    els.historyMonthFilter.value = months.indexOf(currentMonthValue) !== -1 ? currentMonthValue : '';
    state.historyMonthFilter = els.historyMonthFilter.value;

    var filtered = records.filter(function (r) {
      if (state.historyMonthFilter && r.date.substring(0, 7) !== state.historyMonthFilter) return false;
      if (state.historySearch && r.date.toLowerCase().indexOf(state.historySearch) === -1) return false;
      return true;
    });

    var noRecordsAtAll = records.length === 0;
    var noMatches = !noRecordsAtAll && filtered.length === 0;

    els.historyEmpty.hidden = !noRecordsAtAll;
    els.historyNoResults.hidden = !noMatches;
    els.historyTableWrap.hidden = noRecordsAtAll || noMatches;
    els.historyCards.hidden = noRecordsAtAll || noMatches;

    if (noRecordsAtAll || noMatches) {
      els.historyTableBody.innerHTML = '';
      els.historyCards.innerHTML = '';
      return;
    }

    els.historyTableBody.innerHTML = filtered.map(function (r) {
      return '<tr>' +
        '<td>' + formatDateDisplay(r.date) + '</td>' +
        '<td class="num">' + formatNumber(r.usedCodes) + '</td>' +
        '<td class="num">' + formatHuf(r.commission) + '</td>' +
        '<td><div class="row-actions">' +
          '<button class="btn-icon" data-action="edit" data-id="' + r.id + '">Szerkesztés</button>' +
          '<button class="btn-icon danger" data-action="delete" data-id="' + r.id + '">Törlés</button>' +
        '</div></td>' +
      '</tr>';
    }).join('');

    els.historyCards.innerHTML = filtered.map(function (r) {
      return '<div class="record-card">' +
        '<div class="record-card-main">' +
          '<span class="record-card-date">' + formatDateDisplay(r.date) + '</span>' +
          '<span class="record-card-sub">' + formatNumber(r.usedCodes) + ' kód</span>' +
        '</div>' +
        '<div class="record-card-main" style="align-items:flex-end">' +
          '<span class="record-card-commission">' + formatHuf(r.commission) + '</span>' +
          '<div class="record-card-actions">' +
            '<button class="btn-icon" data-action="edit" data-id="' + r.id + '">Szerkesztés</button>' +
            '<button class="btn-icon danger" data-action="delete" data-id="' + r.id + '">Törlés</button>' +
          '</div>' +
        '</div>' +
      '</div>';
    }).join('');

    bindRowActions();
  }

  function bindRowActions() {
    document.querySelectorAll('[data-action="edit"]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var record = state.records.find(function (r) { return String(r.id) === btn.dataset.id; });
        if (record) enterEditMode(record);
      });
    });
    document.querySelectorAll('[data-action="delete"]').forEach(function (btn) {
      btn.addEventListener('click', function () { openConfirmModal(btn.dataset.id); });
    });
  }

  // -------------------------------------------------------------------
  // Delete confirmation
  // -------------------------------------------------------------------

  function openConfirmModal(id) {
    state.deleteTargetId = id;
    els.confirmModal.hidden = false;
  }

  function closeConfirmModal() {
    state.deleteTargetId = null;
    els.confirmModal.hidden = true;
  }

  function onConfirmDelete() {
    var id = state.deleteTargetId;
    if (id === null) return;
    setButtonBusy(els.confirmOk, true, 'Törlés…');

    apiPost('deleteRecord', { id: id })
      .then(function (data) {
        state.records = data.records || [];
        state.settings = data.settings || state.settings;
        state.summary = data.summary || state.summary;
        renderAll();
        showToast('Rögzítés törölve.', 'success');
        closeConfirmModal();
      })
      .catch(function (err) { showToast(friendlyError(err), 'error'); })
      .finally(function () { setButtonBusy(els.confirmOk, false, 'Törlés'); });
  }

  // -------------------------------------------------------------------
  // Settings
  // -------------------------------------------------------------------

  function renderSettings() {
    var rate = state.settings.commissionPerCode || 500;
    els.settingsCurrentRate.textContent = formatHuf(rate);
    if (document.activeElement !== els.fieldRate) {
      els.fieldRate.value = rate;
    }
  }

  function onSubmitSettings(e) {
    e.preventDefault();
    els.errorRate.textContent = '';

    var rate = Number(els.fieldRate.value);
    if (!els.fieldRate.value || isNaN(rate) || rate <= 0) {
      els.errorRate.textContent = 'Adjon meg egy pozitív számot.';
      return;
    }

    setButtonBusy(els.btnSaveSettings, true, 'Mentés…');
    apiPost('updateSettings', { commissionPerCode: rate })
      .then(function (data) {
        state.records = data.records || [];
        state.settings = data.settings || state.settings;
        state.summary = data.summary || state.summary;
        renderAll();
        showToast('Jutalék mérték frissítve.', 'success');
      })
      .catch(function (err) { showToast(friendlyError(err), 'error'); })
      .finally(function () { setButtonBusy(els.btnSaveSettings, false, 'Beállítás mentése'); });
  }

  // -------------------------------------------------------------------
  // UI helpers
  // -------------------------------------------------------------------

  function setLoading(isLoading, text) {
    els.loadingOverlay.hidden = !isLoading;
    if (text) els.loadingText.textContent = text;
  }

  function setButtonBusy(btn, busy, label) {
    btn.disabled = busy;
    btn.textContent = label;
  }

  function showToast(message, type) {
    var toast = document.createElement('div');
    toast.className = 'toast ' + (type || '');
    toast.textContent = message;
    els.toastContainer.appendChild(toast);
    setTimeout(function () {
      toast.remove();
    }, 3200);
  }

  function showBanner(message) {
    els.banner.textContent = message;
    els.banner.hidden = false;
  }

  function hideBanner() {
    els.banner.hidden = true;
  }

  function friendlyError(err) {
    var msg = (err && err.message) || '';
    if (msg && msg.length < 140 && !/script error|typeerror|referenceerror/i.test(msg)) return msg;
    return 'Hiba történt. Kérjük, próbálja újra.';
  }

  // -------------------------------------------------------------------
  // Formatting helpers (Hungarian conventions)
  // -------------------------------------------------------------------

  var HU_MONTHS = ['január', 'február', 'március', 'április', 'május', 'június',
    'július', 'augusztus', 'szeptember', 'október', 'november', 'december'];
  var HU_MONTHS_SHORT = ['jan.', 'febr.', 'márc.', 'ápr.', 'máj.', 'jún.',
    'júl.', 'aug.', 'szept.', 'okt.', 'nov.', 'dec.'];

  function formatHuf(n) {
    return formatNumber(n) + ' HUF';
  }

  function formatNumber(n) {
    n = Number(n) || 0;
    return n.toLocaleString('hu-HU');
  }

  function formatDateDisplay(iso) {
    var parts = iso.split('-');
    var monthIdx = Number(parts[1]) - 1;
    return parts[0] + '. ' + HU_MONTHS_SHORT[monthIdx] + ' ' + Number(parts[2]) + '.';
  }

  function monthLabelFromKey(key) {
    var parts = key.split('-');
    var monthIdx = Number(parts[1]) - 1;
    return parts[0] + '. ' + HU_MONTHS[monthIdx];
  }

  function shortMonthLabel(fullLabel) {
    var monthName = fullLabel.split(' ')[1] || fullLabel;
    var idx = HU_MONTHS.indexOf(monthName);
    return idx === -1 ? monthName.substring(0, 4) : HU_MONTHS_SHORT[idx];
  }

  function toIsoDate(d) {
    var y = d.getFullYear();
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + day;
  }

  function uniqueSorted(arr) {
    var seen = {};
    var out = [];
    arr.forEach(function (v) {
      if (!seen[v]) { seen[v] = true; out.push(v); }
    });
    out.sort();
    return out;
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

})();
