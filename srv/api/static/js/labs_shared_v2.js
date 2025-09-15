(function(){
  'use strict';

  const { $, $$, storageGet, storageSet, parseISODate, getDateRange, makeDateSelect } = window.hpLabsShared;
  const { fetchMedications, addMedicationOverlays } = window.hpLabsOverlays;

  const SEL = '.hp-labs-shared';

  // CATEGORY MAP for metrics grouping
  const CATEGORY_MAP = {
    // Complete Blood Count (CBC)
    'wbc': 'Complete Blood Count',
    'rbc': 'Complete Blood Count',
    'hgb': 'Complete Blood Count',
    'hct': 'Complete Blood Count',
    'plt': 'Complete Blood Count',
    'platelet count': 'Complete Blood Count',
    'hemoglobin a1c': 'Complete Blood Count',
    'mcv': 'Complete Blood Count',
    'mch': 'Complete Blood Count',
    'mchc': 'Complete Blood Count',
    'mpv': 'Complete Blood Count',

    // Liver Function Tests (LFT)
    'alt': 'Liver Function Tests',
    'ast': 'Liver Function Tests',
    'alp': 'Liver Function Tests',
    'ggt': 'Liver Function Tests',
    'bilirubin total': 'Liver Function Tests',
    'bilirubin direct': 'Liver Function Tests',
    'albumin': 'Liver Function Tests',

    // Metabolic Panel
    'glucose': 'Metabolic Panel',
    'na': 'Metabolic Panel',
    'k': 'Metabolic Panel',
    'cl': 'Metabolic Panel',
    'bicarbonate': 'Metabolic Panel',
    'creatinine': 'Metabolic Panel',
    'bun': 'Metabolic Panel',
    'calcium corrected for albumin': 'Metabolic Panel',

    // Hormones
    'testosterone': 'Hormones',
    'thyroid stimulating hormone': 'Hormones',
    'tsh': 'Hormones',
    'prolactin': 'Hormones',
    'cortisol (serum)': 'Hormones',
    'fsh': 'Hormones',

    // Lipids
    'cholesterol total': 'Lipids',
    'hdl': 'Lipids',
    'ldl': 'Lipids',
    'triglycerides': 'Lipids',
    'chol/hdl ratio': 'Lipids',

    // Coagulation
    'pt': 'Coagulation',
    'inr': 'Coagulation',
    'aptt': 'Coagulation',

    // Urine Tests
    'urine creatinine': 'Urine Tests',
    'urine glucose': 'Urine Tests',
    'urine ketones': 'Urine Tests',
    'urine protein': 'Urine Tests',
    'urine rbc/hpf': 'Urine Tests',
    'urine wbc/hpf': 'Urine Tests',
    'urine blood': 'Urine Tests',

    // Miscellaneous
    'weight': 'Miscellaneous',
    'body mass index': 'Miscellaneous',
    'body surface area': 'Miscellaneous',
    'calculated osmolality': 'Miscellaneous',
    'estimated glomerular filtration rate': 'Miscellaneous',
    'sed rate (knox)': 'Miscellaneous',
    'iron': 'Miscellaneous',
  };

  // A superset of all known lab metrics available, dynamically loaded
  let ALL_METRICS = [];

  let _dataCache = null;
  let _personId = null;
  let _labMedEvents = [];

  async function fetchAllLabs(personId, startDate, endDate){
    const baseUrl = `/labs/${encodeURIComponent(personId)}/all-series`;
    const params = new URLSearchParams();
    if(startDate) params.set('start_date', startDate);
    if(endDate) params.set('end_date', endDate);
    const response = await fetch(baseUrl + '?' + params.toString(), {cache:'no-store'});
    if(!response.ok) throw new Error('Failed to load all labs');
    return response.json();
  }

  async function fetchJSON(url, opts = {}) {
  const controller = new AbortController();
  const timeoutMs = opts.timeoutMs ?? 15000;
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const r = await fetch(url, { signal: controller.signal, cache: 'no-store' });
    if (!r.ok) {
      const text = await r.text().catch(() => '');
      throw new Error(`${url} ${r.status} ${text}`.trim());
    }
    return await r.json();
  } finally {
    clearTimeout(id);
  }
}

async function fetchLabMetadata(personId){
    const baseUrl = `/labs/${encodeURIComponent(personId)}/labs-metadata`;
    const response = await fetch(baseUrl, { cache: 'no-store' });
    if(!response.ok) throw new Error('Failed to load labs metadata');
    return response.json();
  }

  function renderControlsWithGroups(el, metadata, initialChecked = []) {
    const controls = $('.hp-labs-controls', el);
    controls.innerHTML = '';

    if (!_dataCache || _dataCache.length === 0) {
      controls.textContent = 'No lab data available for date range selection';
      return;
    }

    const { minDate, maxDate } = getDateRange(_dataCache);

    const storedStart = storageGet('shared_labs_date_start', minDate.toISOString().slice(0, 10));
    const storedEnd = storageGet('shared_labs_date_end', maxDate.toISOString().slice(0, 10));

    const groupsMap = {};
    metadata.forEach(m => {
      const labelLower = (m.label || '').toLowerCase();
      let group = 'Other';
      for (const [key, cat] of Object.entries(CATEGORY_MAP)) {
        if (labelLower.includes(key)) {
          group = cat;
          break;
        }
      }
      if (!groupsMap[group]) groupsMap[group] = [];
      groupsMap[group].push(m);
    });

    console.log('Labs grouped metadata:', groupsMap);
    for (const [group, metrics] of Object.entries(groupsMap)) {
      const groupContainer = document.createElement('div');
      groupContainer.style.marginBottom = '12px';

      const groupHeader = document.createElement('h3');
      groupHeader.textContent = group;
      groupHeader.style.marginBottom = '6px';
      groupContainer.appendChild(groupHeader);

      metrics.forEach(m => {
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.value = m.metric;
        cb.id = 'cb_' + m.metric;
        cb.checked = initialChecked.includes(m.metric);

        const label = document.createElement('label');
        label.htmlFor = cb.id;
        label.textContent = m.label || m.metric;
        label.style.marginLeft = '6px';

        const div = document.createElement('div');
        div.appendChild(cb);
        div.appendChild(label);
        groupContainer.appendChild(div);
      });

      controls.appendChild(groupContainer);
    }

    // Date selectors
    const dateRangeContainer = document.createElement('div');
    dateRangeContainer.style.display = 'flex';
    dateRangeContainer.style.alignItems = 'center';

    const startSelect = makeDateSelect('shared_labs_start_date', 'Start Date', storedStart, minDate, maxDate);
    const endSelect = makeDateSelect('shared_labs_end_date', 'End Date', storedEnd, minDate, maxDate);

    dateRangeContainer.appendChild(startSelect);
    dateRangeContainer.appendChild(endSelect);
    controls.appendChild(dateRangeContainer);

    controls.addEventListener('change', (e) => {
      if (e.target.type === 'checkbox') {
        renderCharts(el, _labMedEvents);
      } else if (e.target.tagName === 'SELECT') {
        const start = $('#shared_labs_start_date').value;
        const end = $('#shared_labs_end_date').value;
        if (start > end) {
          alert('Start date must be before or equal to end date.');
          if (e.target.id === 'shared_labs_start_date') e.target.value = end;
          else e.target.value = start;
          return;
        }
        storageSet('shared_labs_date_start', start);
        storageSet('shared_labs_date_end', end);
        loadAndRender(el, start, end);
      }
    });
  }

  function renderCharts(el, medEvents = []) {
    if(!_dataCache) return;

    const checkedMetrics = Array.from(el.querySelectorAll('.hp-labs-controls input[type=checkbox]:checked'))
      .map(cb => cb.value);

    const body = $('.hp-labs-body', el);
    body.innerHTML = '';

    const datasetsMap = {};
    checkedMetrics.forEach(m => datasetsMap[m] = []);

    _dataCache.forEach(metricData => {
      const m = metricData.metric;
      if(!datasetsMap[m]) return;
      metricData.series.forEach(point => {
        datasetsMap[m].push({ x: point.t_utc, y: point.v });
      });
    });

    const canvas = document.createElement('canvas');
    body.appendChild(canvas);

    const ctx = canvas.getContext('2d');

    const colors = ['#2563eb', '#f97316', '#4ade80', '#f43f5e', '#60a5fa', '#a78bfa', '#fca5a5', '#84cc16', '#22d3ee', '#fbbf24'];

    const datasets = checkedMetrics.map((m, idx) => ({
      label: m,
      data: datasetsMap[m],
      borderColor: colors[idx % colors.length],
      fill: false,
      tension: 0.3,
      pointRadius: 2
    }));

    if(window._labsSharedChartInstance) window._labsSharedChartInstance.destroy();

    const plugins = [];
    // if(medEvents.length > 0) {
    //   plugins.push(makeMedOverlayPlugin(medEvents, { color: '#f43f5e', label: 'Medications' }));
    // }

    window._labsSharedChartInstance = new Chart(ctx, {
      type: 'line',
      data: { datasets },
      options: {
        responsive: true,
        parsing: { xAxisKey: 'x', yAxisKey: 'y' },
        scales: {
          x: { type: 'time', time: { unit: 'day' }, title: { display: true, text: 'Date' } },
          y: { title: { display: true, text: 'Value' } }
        },
        plugins: { legend: { display: true } },
        plugins
      }
    });
  }

  async function loadAndRender(el, startDate, endDate) {
    try {
      const personId = (el && el.dataset && el.dataset.personId) ? el.dataset.personId : 'me';
      const [seriesRes, metaRes] = await Promise.allSettled([
        fetchAllLabs(personId, startDate, endDate),
        fetchLabMetadata(personId)
      ]);
      if (seriesRes.status !== 'fulfilled') {
        console.error('Error loading shared labs series:', seriesRes.reason);
        showError('Could not load lab series. Please retry.');
        return;
      }
      const series = Array.isArray(seriesRes.value) ? seriesRes.value : [];
      _dataCache = series;

      const meta = metaRes.status === 'fulfilled' ? (metaRes.value || []) : [];
      const blacklist = new Set(['hr', 'spo2']);
      const filteredMetadata = (meta || []).filter(m => m && m.metric && !blacklist.has(String(m.metric).toLowerCase()));

      const metricsFromMeta = filteredMetadata.map(m => m.metric);
      const metricsFromSeries = Array.from(new Set(series.map(s => s.metric))).filter(Boolean);
      const metricList = metricsFromMeta.length ? metricsFromMeta : metricsFromSeries;
      ALL_METRICS = metricList;

      const initialChecked = metricList.slice(0, Math.min(5, metricList.length));
      const displayMeta = filteredMetadata.length ? filteredMetadata : metricList.map(m => ({ metric: m, label: m }));

      renderControlsWithGroups(el, displayMeta, initialChecked);
      renderCharts(el, _labMedEvents);
    } catch (e) {
      console.warn('Error loading shared labs:', e);
      showError('Unable to render lab graphs.');
    }
  }

  // Expose loader for hotfix boot script
  window.loadAndRender = function(el, startDate, endDate) {
    if (!el) el = document.querySelector(SEL);
    if (el) return loadAndRender(el, startDate, endDate);
  };

  function showError(msg) {
  const el = document.querySelector('#labs-shared-error');
  if (el) { el.textContent = msg; el.classList.remove('hidden'); }
  else { console.error(msg); }
}

function boot() {
    document.querySelectorAll(SEL).forEach(el => loadAndRender(el));
  }

  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

})();
