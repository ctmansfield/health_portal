(function(){
  'use strict';

  // Add cache variables
  let _dataCache = null;
  let _labMedEvents = [];

  // CATEGORY_MAP: Grouping for lab metrics
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

    // New panels
    'urine': 'Urine Tests',
    'drug screen': 'Drug Screen',
    'antibodies': 'Antibodies'
    // Add other if applicable
  };

  // Canonical metric key map to unify equivalent metric names
  const CANONICAL_MAP = {
    'ha1c': 'hemoglobin a1c',
    'hba1c': 'hemoglobin a1c',
    'hemoglobin a1c': 'hemoglobin a1c',
    'bilirubin total': 'bilirubin total',
    'bilrubin total': 'bilirubin total',
    'bilirubin direct': 'bilirubin direct',
    'bili total': 'bilirubin total',
    'bili direct': 'bilirubin direct',
    // add any other equivalents here
  };

  function canonicalizeMetric(str) {
    const key = str.toLowerCase().trim();
    return CANONICAL_MAP[key] || key;
  }

  const ALIAS_MAP = {
    'albumin': 'albumin',
    'alkaline phosphatase': 'alp',
    'gamma glutamyl transferase': 'ggt',
    'bilirubin': 'bilirubin total',
    '1968-7': 'bilirubin total',
    'alanine aminotransferase': 'alt',
    'alt': 'alt',
    'aspartate aminotransferase': 'ast',
    'ast': 'ast',
    'ggt': 'ggt',
    'bili total': 'bilirubin total',
    'bili direct': 'bilirubin direct',
    'hgb a1c': 'hemoglobin a1c',
    'hemoglobin a1c': 'hemoglobin a1c',

    // Drug Screen examples
    'hcg': 'drug screen',
    'drug screen': 'drug screen',
    'drug test': 'drug screen',

    // Antibodies examples
    'hiv antibodies': 'antibodies',
    'hep b antibodies': 'antibodies',

    // Urine examples
    'urine protein': 'urine',
    'urinalysis': 'urine',
    'urine glucose': 'urine',
    'urine ketones': 'urine'
    // Add other urine metrics as needed
  };

  // Create reverse alias-to-group map to improve panel assignment
  const aliasToGroup = {};
  Object.entries(ALIAS_MAP).forEach(([alias, canonical]) => {
    if(canonical && CATEGORY_MAP[canonical]) {
      aliasToGroup[alias] = CATEGORY_MAP[canonical];
    }
  });

  const VITALS_BLACKLIST = new Set([
    'hr', 'spo2',
    '8867-4',
    '59408-5',
    'heart rate', 'oxygen saturation'
  ]);

  const HIDDEN_PANELS = new Set(['drug screen', 'sti']);

  window.hpLabsSharedV3 = true;

  const { $, $$, storageGet, storageSet, parseISODate, getDateRange, makeDateSelect } = window.hpLabsShared;
  const { fetchMedications, addMedicationOverlays } = window.hpLabsOverlays;

  const SEL = '.hp-labs-shared';

  async function fetchAllLabs(personId, startDate, endDate){
    const baseUrl = `/labs/${encodeURIComponent(personId)}/all-series`;
    const params = new URLSearchParams();
    if(startDate) params.set('start_date', startDate);
    if(endDate) params.set('end_date', endDate);
    const response = await fetch(baseUrl + '?' + params.toString(), {cache:'no-store'});
    if(!response.ok) throw new Error('Failed to load all labs');
    _dataCache = await response.json();
    return _dataCache;
  }

  async function fetchMetricsCatalog(){
    try{
      const r = await fetch('/labs/metrics-catalog', {cache:'no-store'});
      if(!r.ok) return [];
      return await r.json();
    }catch(e){
      return [];
    }
  }

  async function fetchLabMetadata(personId){
    const baseUrl = `/labs/${encodeURIComponent(personId)}/labs-metadata`;
    const response = await fetch(baseUrl, { cache: 'no-store' });
    if(!response.ok) return [];
    return response.json();
  }

  // Modify renderPanelControls to not disable checkboxes blindly and to use aliasToGroup for group assignment
  function renderPanelControls(el, metadata, initialChecked = []) {
    const controls = $('.hp-labs-controls', el);
    controls.innerHTML = '';

    if(!metadata || metadata.length === 0) {
      controls.textContent = 'No lab metrics available';
      return;
    }

    // Group labs by group property, use aliasToGroup to assign group if available
    const panelMap = {};
    metadata.forEach(m => {
      let panel = (m.group || 'Other').toLowerCase();

      // Also try alias-to-group mapping by metric and label
      const metricNorm = m.metric.toLowerCase().trim();
      const labelNorm = (m.label || '').toLowerCase().trim();
      if(aliasToGroup[metricNorm]) panel = aliasToGroup[metricNorm].toLowerCase();
      else if(aliasToGroup[labelNorm]) panel = aliasToGroup[labelNorm].toLowerCase();
      if(HIDDEN_PANELS.has(panel)) return;
      if(!panelMap[panel]) panelMap[panel] = [];
      panelMap[panel].push(m);
    });

    const panels = Object.keys(panelMap).sort((a,b) => {
      if(a === 'other') return 1;
      if(b === 'other') return -1;
      return a.localeCompare(b);
    });

    // Create dropdown to select panel
    const panelSelector = document.createElement('select');
    panelSelector.style.marginBottom = '8px';

    panels.forEach(panel => {
      const option = document.createElement('option');
      option.value = panel;
      option.textContent = panel.charAt(0).toUpperCase() + panel.slice(1);
      panelSelector.appendChild(option);
    });

    controls.appendChild(panelSelector);

    // Container to hold lab checkboxes
    const checkboxContainer = document.createElement('div');
    controls.appendChild(checkboxContainer);

    function renderCheckboxes(panel) {
      const labs = panelMap[panel] || [];
      checkboxContainer.innerHTML = '';
      labs.sort((a,b) => (a.label || a.metric).localeCompare(b.label || b.metric));

      labs.forEach(item => {
        const row = document.createElement('div');
        row.style.display = 'flex';
        row.style.alignItems = 'center';
        row.style.marginBottom = '6px';

        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.value = item.metric || item;
        cb.id = 'cb_' + cb.value;
        cb.checked = initialChecked.includes(cb.value);
        const lbl = document.createElement('label');
        lbl.htmlFor = cb.id;
        lbl.textContent = item.label || cb.value;
        lbl.style.marginLeft = '8px';

        row.appendChild(cb);
        row.appendChild(lbl);
        checkboxContainer.appendChild(row);
      });
    }

    panelSelector.addEventListener('change', () => {
      renderCheckboxes(panelSelector.value);
      renderCharts(el);
    });

    // Initial render
    renderCheckboxes(panelSelector.value);
  }

  function renderCharts(el) {
    if (!_dataCache) return;

    const body = $('.hp-labs-body', el);
    body.innerHTML = '';

    const checkedBoxes = Array.from(el.querySelectorAll('.hp-labs-controls input[type=checkbox]:checked'));

    const metricsByPanel = {};

    checkedBoxes.forEach(cb => {
      const metric = canonicalizeMetric(cb.value.toLowerCase());
      let groupName = 'Other';
      if (aliasToGroup[metric]) {
        groupName = aliasToGroup[metric];
      } else {
        for (const [k, v] of Object.entries(CATEGORY_MAP)) {
          if (metric.includes(k)) {
            groupName = v;
            break;
          }
        }
      }

      if (HIDDEN_PANELS.has(groupName.toLowerCase())) return;
      if (!metricsByPanel[groupName]) metricsByPanel[groupName] = [];
      metricsByPanel[groupName].push(metric);
    });

    console.log('renderCharts - metrics by panel:');
    Object.entries(metricsByPanel).forEach(([panelName, metrics]) => {
      console.log(`Panel: ${panelName}, Metrics: ${metrics.join(', ')}`);
    });

    Object.entries(metricsByPanel).forEach(([panelName, metrics]) => {
      const panelDiv = document.createElement('div');
      panelDiv.className = 'hp-labs-chart-panel';

      const header = document.createElement('h2');
      header.textContent = panelName + ' Panel';
      panelDiv.appendChild(header);

      const canvas = document.createElement('canvas');
      panelDiv.appendChild(canvas);
      body.appendChild(panelDiv);

      const seriesMap = {};
      _dataCache.forEach(md => {
        seriesMap[canonicalizeMetric(md.metric.toLowerCase())] = md.series || [];
      });

      const unitForMetric = {};
      const transformed = {};
      metrics.forEach(m => {
        const s = seriesMap[canonicalizeMetric(m.toLowerCase())] || [];
        console.log(`Panel: ${panelName}, Metric: ${m}, Data points: ${s.length}`);
        if (!s || s.length === 0) {
          transformed[m] = [];
          unitForMetric[m] = '';
          return;
        }

        const vals = s.map(p => (p && p.v !== null) ? Number(p.v) : null).filter(v => v !== null && !Number.isNaN(v));
        const avg = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
        if (m.toLowerCase().includes('spo2') || (avg > 0 && avg <= 2)) {
          unitForMetric[m] = '%';
          transformed[m] = s.map(p => ({ x: p.t_utc, y: (p.v !== null ? Number(p.v) * 100 : null) }));
        } else if (m.toLowerCase().includes('hr') || m.toLowerCase().includes('heart')) {
          unitForMetric[m] = 'bpm';
          transformed[m] = s.map(p => ({ x: p.t_utc, y: (p.v !== null ? Number(p.v) : null) }));
        } else {
          unitForMetric[m] = '';
          transformed[m] = s.map(p => ({ x: p.t_utc, y: (p.v !== null ? Number(p.v) : null) }));
        }
      });

      let axisCount = 0;
      const unitToAxis = {};
      metrics.forEach(m => {
        const u = unitForMetric[m] || '';
        if (!(u in unitToAxis)) {
          unitToAxis[u] = axisCount++ === 0 ? 'y' : 'y' + axisCount;
        }
      });

      const colors = ['#2563eb', '#f97316', '#4ade80', '#f43f5e', '#60a5fa', '#a78bfa', '#fca5a5', '#84cc16', '#22d3ee', '#fbbf24'];

      const datasets = metrics.map((m, idx) => ({
        label: m + (unitForMetric[m] ? ` (${unitForMetric[m]})` : ''),
        data: transformed[m] || [],
        borderColor: colors[idx % colors.length],
        backgroundColor: colors[idx % colors.length],
        fill: false,
        tension: 0.3,
        pointRadius: 2,
        yAxisID: unitToAxis[unitForMetric[m] || ''] || 'y'
      }));

      const scales = {
        x: { type: 'time', time: { unit: 'day' }, title: { display: true, text: 'Date' } }
      };

      const primaryUnit = Object.keys(unitToAxis)[0] || '';
      scales['y'] = { position: 'left', title: { display: !!primaryUnit, text: primaryUnit || 'Value' }, grid: { drawOnChartArea: true } };

      for (const [u, axisId] of Object.entries(unitToAxis)) {
        if (axisId === 'y') continue;
        scales[axisId] = { position: 'right', title: { display: !!u, text: u || '' }, grid: { drawOnChartArea: false }, offset: true };
      }

      if (!window._labsSharedChartInstances) window._labsSharedChartInstances = {};
      if (window._labsSharedChartInstances[panelName]) {
        window._labsSharedChartInstances[panelName].destroy();
        delete window._labsSharedChartInstances[panelName];
      }

      const ctx = canvas.getContext('2d');
      const chart = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
          responsive: true,
          parsing: { xAxisKey: 'x', yAxisKey: 'y' },
          scales,
          plugins: {
            legend: { display: true },
            tooltip: { mode: 'nearest', intersect: false },
            zoom: {
              pan: { enabled: true, mode: 'x' },
              zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: 'x' }
            }
          }
        }
      });

      window._labsSharedChartInstances[panelName] = chart;

      if (_labMedEvents && _labMedEvents.length > 0) {
        try { addMedicationOverlays(chart, _labMedEvents); } catch (e) { console.warn('med overlays failed', e); }
      }
    });
  }

  function dumpCatalogMetrics(catalog) {
    console.log('Catalog dump:');
    catalog.forEach((c) => {
      console.log(`  Metric key: ${c.metric}, Label: ${c.label || '-'}'`);
    });
  }

  async function loadAndRender(el, startDate, endDate) {
    try {
      const personId = (el && el.dataset && el.dataset.personId) ? el.dataset.personId : 'me';
      const params = new URLSearchParams();
      if(startDate) params.set('start_date', startDate);
      if(endDate) params.set('end_date', endDate);

      const [seriesRes, metaRes, catalogRes] = await Promise.allSettled([
        fetch(`/labs/${encodeURIComponent(personId)}/all-series?` + params.toString(), {cache: 'no-store'}).then(r => r.json()),
        fetch(`/labs/${encodeURIComponent(personId)}/labs-metadata`, {cache: 'no-store'}).then(r => r.json()),
        fetchMetricsCatalog()
      ]);

      if(seriesRes.status !== 'fulfilled') {
        console.error('Error loading shared labs series:', seriesRes.reason);
        showError('Could not load lab series. Please retry.');
        return;
      }

      const series = Array.isArray(seriesRes.value) ? seriesRes.value : [];
      _dataCache = series;
      const meta = metaRes.status === 'fulfilled' ? (metaRes.value || []) : [];
      const catalog = catalogRes.status === 'fulfilled' ? (catalogRes.value || []) : [];

      dumpCatalogMetrics(catalog);

      function normalizeKey(str) {
        return str ? str.toLowerCase().trim() : '';
      }

      // Wrap normalizeKey with canonicalizeMetric
      const normalizedAndCanonKey = (str) => canonicalizeMetric(normalizeKey(str));

      const filteredMetadata = (meta || []).filter(m => {
        const k = normalizedAndCanonKey(m.metric);
        return m && m.metric && !VITALS_BLACKLIST.has(k);
      });

      const normalizedCatalog = (catalog || []).map(c => ({
        ...c,
        metric: normalizedAndCanonKey(c.metric),
        label: c.label ? normalizeKey(c.label) : '',
      }));

      const seriesMetrics = Array.from(new Set(
        series.map(s => s.metric).filter(m => !VITALS_BLACKLIST.has(normalizedAndCanonKey(m)))
          .map(normalizedAndCanonKey)
      ));

      const filteredMetaMetrics = filteredMetadata.map(m => normalizedAndCanonKey(m.metric));

      // Build superset metric list: union of catalog, metadata, series, and category map with canonical keys
      const supersetMetricsSet = new Set([
        ...normalizedCatalog.filter(c => !VITALS_BLACKLIST.has(c.metric)).map(c => ALIAS_MAP[c.label] || ALIAS_MAP[c.metric] || c.metric),
        ...filteredMetaMetrics,
        ...seriesMetrics,
        ...Object.keys(CATEGORY_MAP).map(k => normalizedAndCanonKey(k)),
      ]);

      let metricList = Array.from(supersetMetricsSet);

      if(filteredMetaMetrics.length) {
        metricList.sort((a, b) => {
          const ia = filteredMetaMetrics.indexOf(a);
          const ib = filteredMetaMetrics.indexOf(b);
          if(ia === -1 && ib === -1) return a.localeCompare(b);
          if(ia === -1) return 1;
          if(ib === -1) return -1;
          return ia - ib;
        });
      } else {
        metricList.sort();
      }

      // When creating metaMap and displayMeta, map keys via normalizedAndCanonKey accordingly
      const metaMap = {};
      filteredMetadata.forEach(m => {
        metaMap[normalizedAndCanonKey(m.metric)] = m;
      });

      normalizedCatalog.forEach(c => {
        const key = ALIAS_MAP[c.label] || ALIAS_MAP[c.metric] || c.metric;
        if (!(key in metaMap) && !VITALS_BLACKLIST.has(key)) {
          metaMap[key] = { metric: key, label: c.label || key };
        }
      });

      Object.entries(CATEGORY_MAP).forEach(([k, v]) => {
        const normK = normalizedAndCanonKey(k);
        if (!(normK in metaMap)) {
          metaMap[normK] = { metric: normK, label: normK, group: v };
        }
      });

      const initialChecked = metricList.filter(m => seriesMetrics.includes(m)).slice(0, 5);

      const displayMeta = metricList.map(m => {
        const d = metaMap[m] ? Object.assign({}, metaMap[m]) : { metric: m, label: m };
        // Do not set .disabled
        return d;
      });
      renderPanelControls(el, displayMeta, initialChecked);
      renderCharts(el);

      try {
        _labMedEvents = await fetchMedications(personId);
      } catch(e) {
        _labMedEvents = [];
      }

      window.ALL_METRICS = metricList; window._dataCache = _dataCache;
    } catch(e) {
      console.warn('Error loading shared labs:', e);
      showError('Unable to render lab graphs.');
    }
  }

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
