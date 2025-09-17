(function(){
  'use strict';

  let _dataCache = null;
  let _labMedEvents = [];

  window.hpLabsSharedV3 = true;

  const { $, $$, storageGet, storageSet, parseISODate, getDateRange, makeDateSelect } = window.hpLabsShared;
  const { fetchMedications, addMedicationOverlays } = window.hpLabsOverlays;

  const SEL = '.hp-labs-shared';

  const VITALS_BLACKLIST = new Set([
    'hr', 'spo2',
    '8867-4',
    '59408-5',
    'heart rate', 'oxygen saturation'
  ]);

  function canonicalizeMetric(str) {
    const key = str.toLowerCase().trim();
    return key;
  }

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

  function renderPanelControls(el, metadata, initialChecked = []) {
    const controls = $('.hp-labs-controls', el);
    controls.innerHTML = '';

    if (!metadata || metadata.length === 0) {
      controls.textContent = 'No lab metrics available';
      return;
    }

    const HIDDEN_PANELS = new Set(['drug screen', 'sti tests']);

    // Group metadata by group_name lowercase, fallback 'other'
    const panelMap = {};
    metadata.forEach(m => {
      const panel = (m.group_name || 'Other').toLowerCase();
      if (HIDDEN_PANELS.has(panel)) return;
      if (!panelMap[panel]) panelMap[panel] = [];
      panelMap[panel].push(m);
    });

    const panels = Object.keys(panelMap).sort((a, b) => {
      if (a === 'other') return 1;
      if (b === 'other') return -1;
      return a.localeCompare(b);
    });

    const panelSelector = document.createElement('select');
    panelSelector.style.marginBottom = '8px';

    panels.forEach(panel => {
      const option = document.createElement('option');
      option.value = panel;
      option.textContent = panel.charAt(0).toUpperCase() + panel.slice(1);
      panelSelector.appendChild(option);
    });

    controls.appendChild(panelSelector);

    const checkboxContainer = document.createElement('div');
    controls.appendChild(checkboxContainer);

    function renderCheckboxes(panel) {
      const labs = panelMap[panel] || [];
      checkboxContainer.innerHTML = '';
      labs.sort((a, b) => (a.label || a.metric).localeCompare(b.label || b.metric));

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
        cb.disabled = item.disabled || false;

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

    renderCheckboxes(panelSelector.value);
  }

  function renderCharts(el) {
    if (!_dataCache) return;

    const body = $('.hp-labs-body', el);
    body.innerHTML = '';

    const checkedBoxes = Array.from(el.querySelectorAll('.hp-labs-controls input[type=checkbox]:checked'));
    const metricsByPanel = {};

    checkedBoxes.forEach(cb => {
      const metric = cb.value.toLowerCase();
      const groupName = window._metricGroupMap && window._metricGroupMap[metric] ? window._metricGroupMap[metric] : 'Other';

      if (groupName.toLowerCase() === 'drug screen' || groupName.toLowerCase() === 'sti tests') return;

      if (!metricsByPanel[groupName]) metricsByPanel[groupName] = [];
      metricsByPanel[groupName].push(metric);
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
      _dataCache.forEach(md => { seriesMap[md.metric.toLowerCase()] = md.series || []; });

      const unitForMetric = {};
      const transformed = {};
      metrics.forEach(m => {
        const s = seriesMap[m.toLowerCase()] || [];
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
      if (startDate) params.set('start_date', startDate);
      if (endDate) params.set('end_date', endDate);

      const [seriesRes, metaRes, catalogRes] = await Promise.allSettled([
        fetch(`/labs/${encodeURIComponent(personId)}/all-series?` + params.toString(), { cache: 'no-store' }).then(r => r.json()),
        fetch(`/labs/${encodeURIComponent(personId)}/labs-metadata`, { cache: 'no-store' }).then(r => r.json()),
        fetchMetricsCatalog()
      ]);

      if (seriesRes.status !== 'fulfilled') {
        console.error('Error loading shared labs series:', seriesRes.reason);
        showError('Could not load lab series. Please retry.');
        return;
      }

      const series = Array.isArray(seriesRes.value) ? seriesRes.value : [];
      _dataCache = series;
      const meta = metaRes.status === 'fulfilled' ? (metaRes.value || []) : [];
      const catalog = catalogRes.status === 'fulfilled' ? (catalogRes.value || []) : [];

      dumpCatalogMetrics(catalog);

      // Group labs dynamically from backend metadata
      const HIDDEN_PANELS = new Set(['drug screen', 'sti tests']);

      // Filter vitals
      const filteredMetadata = (meta || []).filter(m => {
        const label = m.label || m.metric || '';
        return !VITALS_BLACKLIST.has(label.toLowerCase());
      });

      // Build superset metrics
      const seriesMetrics = Array.from(new Set(series.map(s => s.metric).filter(m => !VITALS_BLACKLIST.has(m.toLowerCase()))));
      const supersetMetricsSet = new Set([
        ...filteredMetadata.map(m => m.metric),
        ...seriesMetrics,
        ...catalog.map(c => c.metric.toLowerCase())
      ]);

      let metricList = Array.from(supersetMetricsSet);
      metricList.sort();
      const metaMap = {};
      filteredMetadata.forEach(m => {
        metaMap[m.metric.toLowerCase()] = m;
      });

      // initial checked
      const initialChecked = metricList.filter(m => seriesMetrics.includes(m)).slice(0, 5);

      const displayMeta = metricList.map(m => {
        const d = metaMap[m] ? Object.assign({}, metaMap[m]) : { metric: m, label: m };
        if (!seriesMetrics.includes(m)) d.disabled = true;
        return d;
      });

      // Build a simple map metric -> groupName for charts
      window._metricGroupMap = {};
      displayMeta.forEach(d => {
        if (d.metric && d.group_name) window._metricGroupMap[d.metric.toLowerCase()] = d.group_name;
      });

      renderPanelControls(el, displayMeta, initialChecked);
      renderCharts(el);

      try {
        _labMedEvents = await fetchMedications(personId);
      } catch (e) {
        _labMedEvents = [];
      }

      window.ALL_METRICS = metricList;
      window._dataCache = _dataCache;
    } catch (e) {
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
