// labs_shared_v3.js — improved: shows full lab catalog, disables metrics without person data
(function(){
  'use strict';

  // Mark v3 present so v2 can opt-out when v3 is available
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
    return response.json();
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

  // render controls - accept items with possible .disabled flag
  function renderControlsWithGroups(el, metadata, initialChecked = []) {
    const controls = $('.hp-labs-controls', el);
    controls.innerHTML = '';

    if (!metadata || metadata.length === 0) {
      controls.textContent = 'No lab metrics available';
      return;
    }

    // header
    const header = document.createElement('div');
    header.style.display = 'flex'; header.style.justifyContent='space-between'; header.style.alignItems='center'; header.style.marginBottom='8px';
    const summary = document.createElement('div'); summary.style.color='#6b7280'; summary.textContent = 'Metrics: ' + metadata.map(m => m.metric).join(', ');
    const btns = document.createElement('div');
    const selAll = document.createElement('button'); selAll.className='btn'; selAll.textContent='Select all'; selAll.addEventListener('click', ()=>{ controls.querySelectorAll('input[type=checkbox]:not(:disabled)').forEach(cb=>cb.checked=true); const evt = new Event('change'); controls.dispatchEvent(evt); });
    const clr = document.createElement('button'); clr.className='btn'; clr.style.background='#6b7280'; clr.textContent='Clear'; clr.addEventListener('click', ()=>{ controls.querySelectorAll('input[type=checkbox]').forEach(cb=>cb.checked=false); controls.dispatchEvent(new Event('change')); });
    btns.appendChild(selAll); btns.appendChild(clr);
    header.appendChild(summary); header.appendChild(btns);
    controls.appendChild(header);

    // groups
    const groupsMap = {};
    metadata.forEach(m => {
      const label = (m.label || m.metric || m).toString();
      // find category by label
      let group = 'Other';
      const labelLower = label.toLowerCase();
      for(const [k,v] of Object.entries(CATEGORY_MAP)){
        if(labelLower.includes(k)) { group = v; break; }
      }
      if(!groupsMap[group]) groupsMap[group]=[];
      groupsMap[group].push(m);
    });

    const groupKeys = Object.keys(groupsMap).sort((a,b)=>{ if(a==='Other') return 1; if(b==='Other') return -1; return a.localeCompare(b); });

    // two-column grid
    controls.style.display='grid'; controls.style.gridTemplateColumns='1fr 1fr'; controls.style.gap='12px';

    groupKeys.forEach(group => {
      const list = groupsMap[group];
      list.sort((a,b)=>( (a.label||a.metric||a).toString().localeCompare((b.label||b.metric||b).toString())  ));
      const cont = document.createElement('div'); cont.dataset.group = group; cont.style.padding='6px';
      const hdr = document.createElement('h3'); hdr.textContent = group + ` (${list.length})`; hdr.style.margin='0 0 6px 0'; cont.appendChild(hdr);
      list.forEach(item => {
        const metricKey = (item.metric || item).toString();
        const row = document.createElement('div'); row.style.display='flex'; row.style.alignItems='center'; row.style.marginBottom='6px';
        const cb = document.createElement('input'); cb.type='checkbox'; cb.value = metricKey; cb.id = 'cb_' + metricKey; if(initialChecked.includes(metricKey)) cb.checked = true;
        if(item.disabled) cb.disabled = true; // mark metrics with no person data as disabled
        const lbl = document.createElement('label'); lbl.htmlFor = cb.id; lbl.textContent = (item.label || metricKey); lbl.style.marginLeft='8px';
        row.appendChild(cb); row.appendChild(lbl); cont.appendChild(row);
      });
      controls.appendChild(cont);
    });

    // date selectors (append at bottom left)
    const dr = document.createElement('div'); dr.style.gridColumn='1 / -1'; dr.style.marginTop='6px';
    // we reuse selects already created by caller if present; caller will re-append
    controls.appendChild(dr);

    controls.addEventListener('change', (e)=>{
      if(e.target.type === 'checkbox') {
        renderCharts(el, _labMedEvents);
      }
    });

    console.log('Rendered controls count:', controls.querySelectorAll('input[type=checkbox]').length);
  }

  // rest of code: reuse renderCharts from v3 (multi-axis) — keep as before
  // For brevity, import renderCharts and loadAndRender from v2 logic adapted in-place below

  // renderCharts: multi-axis plotting and unit heuristics
  function renderCharts(el, medEvents = []) {
    if (!_dataCache) return;

    const checkedMetrics = Array.from(el.querySelectorAll('.hp-labs-controls input[type=checkbox]:checked'))
      .map(cb => cb.value);

    const body = $('.hp-labs-body', el);
    body.innerHTML = '';

    // Build series map
    const seriesMap = {};
    _dataCache.forEach(metricData => {
      if (metricData && metricData.metric) seriesMap[metricData.metric] = metricData.series || [];
    });

    // Normalize & infer units
    const unitForMetric = {};
    const transformed = {};
    checkedMetrics.forEach(m => {
      const s = (seriesMap[m] || []).slice();
      if (!s || s.length === 0) { transformed[m] = []; unitForMetric[m] = ''; return; }
      const vals = s.map(p => (p && p.v != null) ? Number(p.v) : null).filter(v => v != null && !Number.isNaN(v));
      const avg = vals.length ? vals.reduce((a,b)=>a+b,0)/vals.length : 0;
      if (m.toLowerCase().includes('spo2') || (avg > 0 && avg <= 2)) {
        unitForMetric[m] = '%';
        transformed[m] = s.map(p => ({ x: p.t_utc, y: (p.v != null ? Number(p.v) * 100 : null) }));
      } else if (m.toLowerCase().includes('hr') || m.toLowerCase().includes('heart')) {
        unitForMetric[m] = 'bpm';
        transformed[m] = s.map(p => ({ x: p.t_utc, y: (p.v != null ? Number(p.v) : null) }));
      } else {
        unitForMetric[m] = '';
        transformed[m] = s.map(p => ({ x: p.t_utc, y: (p.v != null ? Number(p.v) : null) }));
      }
    });

    // Map units to axes
    const unitToAxis = {};
    let axisCount = 0;
    checkedMetrics.forEach(m => {
      const u = unitForMetric[m] || '';
      if (!(u in unitToAxis)) {
        unitToAxis[u] = (axisCount === 0) ? 'y' : 'y' + axisCount;
        axisCount += 1;
      }
    });

    const colors = ['#2563eb', '#f97316', '#4ade80', '#f43f5e', '#60a5fa', '#a78bfa', '#fca5a5', '#84cc16', '#22d3ee', '#fbbf24'];
    const datasets = checkedMetrics.map((m, idx) => ({
      label: m + (unitForMetric[m] ? ` (${unitForMetric[m]})` : ''),
      data: transformed[m] || [],
      borderColor: colors[idx % colors.length],
      backgroundColor: colors[idx % colors.length],
      fill: false,
      tension: 0.3,
      pointRadius: 2,
      yAxisID: unitToAxis[unitForMetric[m] || ''] || 'y'
    }));

    const scales = { x: { type: 'time', time: { unit: 'day' }, title: { display: true, text: 'Date' } } };
    const primaryUnit = Object.keys(unitToAxis)[0] || '';
    scales['y'] = { position: 'left', title: { display: !!primaryUnit, text: primaryUnit || 'Value' }, grid: { drawOnChartArea: true } };
    for (const [u, axisId] of Object.entries(unitToAxis)) {
      if (axisId === 'y') continue;
      scales[axisId] = { position: 'right', title: { display: !!u, text: u || '' }, grid: { drawOnChartArea: false }, offset: true };
    }

    if (window._labsSharedChartInstance) window._labsSharedChartInstance.destroy();
    const canvas = document.createElement('canvas');
    body.appendChild(canvas);
    window._labsSharedChartInstance = new Chart(canvas.getContext('2d'), {
      type: 'line',
      data: { datasets },
      options: {
        responsive: true,
        parsing: { xAxisKey: 'x', yAxisKey: 'y' },
        scales,
        plugins: { legend: { display: true }, tooltip: { mode: 'nearest', intersect: false } }
      }
    });

    if (_labMedEvents && _labMedEvents.length > 0) {
      try { addMedicationOverlays(window._labsSharedChartInstance, _labMedEvents); } catch (e) { console.warn('med overlays failed', e); }
    }
  }

  // loadAndRender: labs-only (exclude hr/spo2)
  async function loadAndRender(el, startDate, endDate) {
    try {
      const personId = (el && el.dataset && el.dataset.personId) ? el.dataset.personId : 'me';
      const [seriesRes, metaRes, catalogRes] = await Promise.allSettled([
        fetchAllLabs(personId, startDate, endDate),
        fetchLabMetadata(personId),
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

      // labs-only metadata (exclude vitals)
      const filteredMetadata = (meta || []).filter(m => m && m.metric && !['hr','spo2'].includes(String(m.metric).toLowerCase()));
      const metricsFromSeries = Array.from(new Set(series.map(s => s.metric))).filter(Boolean).filter(m => !['hr','spo2'].includes(String(m).toLowerCase()));

      // Build superset metric list: union of catalog, person metadata, and series (labs only)
      const catalogMetrics = (catalog || []).map(c => c.metric).filter(Boolean).map(String);
      const metaMetrics = filteredMetadata.map(m => String(m.metric));
      const seriesMetrics = metricsFromSeries.map(m => String(m));
      const metricSet = new Set([...catalogMetrics, ...metaMetrics, ...seriesMetrics]);
      let metricList = Array.from(metricSet);

      // Sort metricList by metadata order if available, else alphabetically
      if (metaMetrics && metaMetrics.length) {
        metricList.sort((a,b) => {
          const ia = metaMetrics.indexOf(a);
          const ib = metaMetrics.indexOf(b);
          if (ia === -1 && ib === -1) return a.localeCompare(b);
          if (ia === -1) return 1;
          if (ib === -1) return -1;
          return ia - ib;
        });
      } else {
        metricList.sort();
      }

      // initial checked: prefer metrics that have series data
      const initialChecked = metricList.filter(m => seriesMetrics.includes(m)).slice(0, Math.min(5, metricList.length));

      // displayMeta: include disabled flag for metrics with no person series
      const metaMap = (filteredMetadata || []).reduce((acc, it) => { acc[it.metric] = it; return acc; }, {});
      const displayMeta = metricList.map(m => {
        const base = metaMap[m] ? Object.assign({}, metaMap[m]) : { metric: m, label: m };
        if (!seriesMetrics.includes(m)) base.disabled = true; // mark metrics without person data
        return base;
      });

      try { _labMedEvents = await fetchMedications(personId); } catch(e) { _labMedEvents = []; }

      // expose debug
      window.ALL_METRICS = metricList; window._dataCache = _dataCache;

      renderControlsWithGroups(el, displayMeta, initialChecked);
      renderCharts(el, _labMedEvents);
    } catch (e) {
      console.warn('Error loading shared labs:', e);
      showError('Unable to render lab graphs.');
    }
  }

})();
