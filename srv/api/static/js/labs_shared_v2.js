(function(){
  'use strict';

  // If v3 is present, no-op to avoid duplicate boot behavior
  if (typeof window !== 'undefined' && window.hpLabsSharedV3) {
    console.log('labs_shared_v3 present — skipping labs_shared_v2 boot');
    return;
  }

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

    // Debug summary: show loaded metric names at top of controls
    const summaryDiv = document.createElement('div');
    summaryDiv.style.fontSize = '0.9rem';
    summaryDiv.style.marginBottom = '8px';
    const metricNames = (metadata || []).map(m => m.metric).filter(me => !['hr','spo2'].includes(String(me).toLowerCase())).join(', ');
    summaryDiv.textContent = metricNames ? `Loaded metrics: ${metricNames}` : '';
    if (summaryDiv.textContent) controls.appendChild(summaryDiv);

    const groupsMap = {};
    const localBlacklist = new Set(['hr','spo2']);
    metadata.forEach(m => {
      if (!m || !m.metric) return;
      if (localBlacklist.has(String(m.metric).toLowerCase())) return;
      // Exclude vitals (hr, spo2) from the labs metadata
      if (!m || !m.metric) return;
      const metLower = String(m.metric).toLowerCase();
      if (['hr','spo2'].includes(metLower)) return;

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
    // debug: report how many controls rendered
    console.log('Rendered controls count:', controls.querySelectorAll('input[type=checkbox]').length);
  }

  function renderCharts(el, medEvents = []) {
    if (!_dataCache) return;

    const checkedMetrics = Array.from(el.querySelectorAll('.hp-labs-controls input[type=checkbox]:checked'))
      .map(cb => cb.value);

    const body = $('.hp-labs-body', el);
    body.innerHTML = '';

    // Build a mapping metric -> series
    const seriesMap = {};
    _dataCache.forEach(metricData => {
      if (metricData && metricData.metric) seriesMap[metricData.metric] = metricData.series || [];
    });

    // Heuristic unit inference and normalization
    const unitForMetric = {}; // metric -> unit string
    const transformedData = {}; // metric -> [{x,y}]

    checkedMetrics.forEach(m => {
      const s = (seriesMap[m] || []).slice();
      if (!s || s.length === 0) { transformedData[m] = []; unitForMetric[m] = ''; return; }
      // infer unit: common cases
      let unit = '';
      // If metric name suggests spo2 or values are fractional < 2 -> percent
      const vals = s.map(p => (p && p.v != null) ? Number(p.v) : null).filter(v => v != null && !Number.isNaN(v));
      const avg = vals.length ? vals.reduce((a,b)=>a+b,0)/vals.length : 0;
      if (m.toLowerCase().includes('spo2') || (avg > 0 && avg <= 2)) {
        unit = '%';
        transformedData[m] = s.map(p => ({ x: p.t_utc, y: (p.v != null ? Number(p.v) * 100 : null) }));
      } else if (m.toLowerCase().includes('hr') || m.toLowerCase().includes('heart') ) {
        unit = 'bpm';
        transformedData[m] = s.map(p => ({ x: p.t_utc, y: (p.v != null ? Number(p.v) : null) }));
      } else {
        // default: leave numeric as-is
        transformedData[m] = s.map(p => ({ x: p.t_utc, y: (p.v != null ? Number(p.v) : null) }));
      }
      unitForMetric[m] = unit || '';
    });

    // Build axes mapping: primary axis 'y' is left, others stacked on right (y1,y2...)
    const unitToAxis = {};
    const axes = {};
    let axisCount = 0;
    checkedMetrics.forEach(m => {
      const u = unitForMetric[m] || '';
      if (!(u in unitToAxis)) {
        const axisId = axisCount === 0 ? 'y' : 'y' + axisCount;
        unitToAxis[u] = axisId;
        axisCount += 1;
      }
    });

    // Create Chart datasets with yAxisID and label including unit
    const colors = ['#2563eb', '#f97316', '#4ade80', '#f43f5e', '#60a5fa', '#a78bfa', '#fca5a5', '#84cc16', '#22d3ee', '#fbbf24'];
    const datasets = checkedMetrics.map((m, idx) => ({
      label: m + (unitForMetric[m] ? ` (${unitForMetric[m]})` : ''),
      data: transformedData[m] || [],
      borderColor: colors[idx % colors.length],
      backgroundColor: colors[idx % colors.length],
      fill: false,
      tension: 0.3,
      pointRadius: 2,
      yAxisID: unitToAxis[unitForMetric[m] || ''] || 'y'
    }));

    // Build scales config
    const scales = {
      x: { type: 'time', time: { unit: 'day' }, title: { display: true, text: 'Date' } }
    };

    // Primary axis (y) = left
    const primaryUnit = Object.keys(unitToAxis)[0] || '';
    scales['y'] = { position: 'left', title: { display: !!primaryUnit, text: primaryUnit || 'Value' }, grid: { drawOnChartArea: true } };

    // Other axes on right
    let axisIndex = 1;
    for (const [u, axisId] of Object.entries(unitToAxis)) {
      if (axisId === 'y') continue;
      scales[axisId] = { position: 'right', title: { display: !!u, text: u || '' }, grid: { drawOnChartArea: false }, offset: true };
      axisIndex += 1;
    }

    if (window._labsSharedChartInstance) window._labsSharedChartInstance.destroy();

    window._labsSharedChartInstance = new Chart(body.appendChild(document.createElement('canvas')).getContext('2d'), {
      type: 'line',
      data: { datasets },
      options: {
        responsive: true,
        parsing: { xAxisKey: 'x', yAxisKey: 'y' },
        scales,
        plugins: {
          legend: { display: true },
          tooltip: { mode: 'nearest', intersect: false }
        }
      }
    });

    // Attach medication overlays if any
    if (_labMedEvents && _labMedEvents.length > 0) {
      try { addMedicationOverlays(window._labsSharedChartInstance, _labMedEvents); } catch (e) { console.warn('Failed to add med overlays', e); }
    }
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
      // Exclude vitals from metadata and series: this shared labs UI is labs-only
      const filteredMetadata = (meta || []).filter(m => m && m.metric && !['hr','spo2'].includes(String(m.metric).toLowerCase()));

      const metricsFromMeta = filteredMetadata.map(m => m.metric);
      const metricsFromSeries = Array.from(new Set(series.map(s => s.metric))).filter(Boolean).filter(m => !['hr','spo2'].includes(String(m).toLowerCase()));

      // Use union of metadata and series-derived metrics
      let metricList = Array.from(new Set([...(metricsFromMeta || []), ...(metricsFromSeries || [])]));
      // Remove any remaining vitals defensively
      metricList = metricList.filter(m => !['hr','spo2'].includes(String(m).toLowerCase()));

      ALL_METRICS = metricList;
      window.ALL_METRICS = ALL_METRICS;
      window._dataCache = _dataCache;

      // Default checked: first up to 5 lab metrics
      const initialChecked = metricList.slice(0, Math.min(5, metricList.length));

      // Build display metadata aligned with chosen metricList
      const metaMap = (filteredMetadata || []).reduce((acc, it) => { acc[it.metric] = it; return acc; }, {});
      const displayMeta = metricList.map(m => metaMap[m] || { metric: m, label: m });

      // Fetch medication events but do not treat vitals as meds
      try {
        _labMedEvents = await fetchMedications(personId);
      } catch (e) {
        _labMedEvents = [];
      }

      renderControlsWithGroups(el, displayMeta, initialChecked);
      renderCharts(el, _labMedEvents);

      // Show note if no medication events available
      const controls = document.querySelector('.hp-labs-controls');
      if (controls) {
        let note = controls.querySelector('.hp-labs-med-note');
        if (!_labMedEvents || _labMedEvents.length === 0) {
          if (!note) {
            note = document.createElement('div');
            note.className = 'hp-labs-med-note';
            note.style.marginTop = '8px';
            note.style.fontStyle = 'italic';
            note.textContent = 'No medication events available for this person.';
            controls.appendChild(note);
          } else {
            note.textContent = 'No medication events available for this person.';
          }
        } else {
          if (note) note.remove();
        }
      }
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
