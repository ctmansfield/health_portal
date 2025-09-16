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
  };

  // Extended alias map for catalog labels and keys to canonical metric keys used in CATEGORY_MAP
  const ALIAS_MAP = {
    'albumin': 'albumin',
    'alkaline phosphatase': 'alp',
    'gamma glutamyl transferase': 'ggt',
    'bilirubin': 'bilirubin total',
    '1968-7': 'bilirubin total', // LOINC code from catalog
    'alanine aminotransferase': 'alt',
    'alt': 'alt',
    'aspartate aminotransferase': 'ast',
    'ast': 'ast',
    'ggt': 'ggt',
    'bili total': 'bilirubin total',
    'bili direct': 'bilirubin direct',
    'hgb a1c': 'hemoglobin a1c',
    'hemoglobin a1c': 'hemoglobin a1c',
  };

  // Extended vitals blacklist including known LOINC codes and label variants
  const VITALS_BLACKLIST = new Set([
    'hr', 'spo2',
    '8867-4',
    '59408-5',
    'heart rate', 'oxygen saturation'
  ]);

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

  // Modified renderControlsWithGroups to add date selectors and wiring
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
    const summary = document.createElement('div'); summary.style.color='#6b7280'; summary.style.flex = '1';
    summary.textContent = 'Metrics: ' + metadata.map(m => m.metric).join(', ');
    const btns = document.createElement('div');
    const selAll = document.createElement('button'); selAll.className='btn'; selAll.textContent='Select all'; selAll.addEventListener('click', ()=>{ controls.querySelectorAll('input[type=checkbox]:not(:disabled)').forEach(cb=>cb.checked=true); controls.dispatchEvent(new Event('change')); });
    const clr = document.createElement('button'); clr.className='btn'; clr.style.background='#6b7280'; clr.textContent='Clear'; clr.addEventListener('click', ()=>{ controls.querySelectorAll('input[type=checkbox]').forEach(cb=>cb.checked=false); controls.dispatchEvent(new Event('change')); });
    btns.appendChild(selAll); btns.appendChild(clr);
    header.appendChild(summary); header.appendChild(btns);

    controls.appendChild(header);

    // groups
    const groupsMap = {};
    metadata.forEach(m => {
      const label = (m.label || m.metric || m).toString();
      let group = 'Other';
      const labelLower = label.toLowerCase();
      for(const [k,v] of Object.entries(CATEGORY_MAP)){
        if(labelLower.includes(k)) { group = v; break; }
      }
      if(!groupsMap[group]) groupsMap[group]=[];
      groupsMap[group].push(m);
    });

    const groupKeys = Object.keys(groupsMap).sort((a,b)=>{ if(a==='Other') return 1; if(b==='Other') return -1; return a.localeCompare(b); });

    controls.style.display='grid'; controls.style.gridTemplateColumns='1fr 1fr'; controls.style.gap='12px';

    groupKeys.forEach(group => {
      const list = groupsMap[group];
      list.sort((a,b)=>( (a.label||a.metric||a).toString().localeCompare((b.label||b.metric||b).toString()) ));
      const cont = document.createElement('div'); cont.dataset.group = group; cont.style.padding='6px';
      const hdr = document.createElement('h3'); hdr.textContent = group + ` (${list.length})`;
      hdr.style.margin='0 0 6px 0'; cont.appendChild(hdr);

      list.forEach(item => {
        const metricKey = (item.metric || item).toString();
        const row = document.createElement('div'); row.style.display='flex'; row.style.alignItems='center'; row.style.marginBottom='6px';
        const cb = document.createElement('input'); cb.type='checkbox'; cb.value = metricKey; cb.id = 'cb_' + metricKey; cb.checked = !item.disabled;
        if(item.disabled) cb.disabled = true;
        const lbl = document.createElement('label'); lbl.htmlFor = cb.id; lbl.textContent = (item.label || metricKey); lbl.style.marginLeft='8px';
        row.appendChild(cb); row.appendChild(lbl); cont.appendChild(row);
      });
      controls.appendChild(cont);
    });

    // date selectors container
    const dateRangeCont = document.createElement('div');
    dateRangeCont.style.gridColumn = '1 / -1';
    dateRangeCont.style.marginTop = '12px';
    dateRangeCont.style.display = 'flex';
    dateRangeCont.style.justifyContent = 'flex-start';
    dateRangeCont.style.alignItems = 'center';
    dateRangeCont.style.gap = '12px';

    const minDate = getDateRange(_dataCache).minDate.toISOString().slice(0,10);
    const maxDate = getDateRange(_dataCache).maxDate.toISOString().slice(0,10);

    const storedStart = storageGet('shared_labs_date_start', minDate);
    const storedEnd = storageGet('shared_labs_date_end', maxDate);

    const startLabel = document.createElement('label');
    startLabel.textContent = 'Start Date: ';
    startLabel.htmlFor = 'shared_labs_start_date';
    const startSelect = document.createElement('input');
    startSelect.type = 'date';
    startSelect.id = 'shared_labs_start_date';
    startSelect.min = minDate;
    startSelect.max = maxDate;
    startSelect.value = storedStart;

    const endLabel = document.createElement('label');
    endLabel.textContent = 'End Date: ';
    endLabel.htmlFor = 'shared_labs_end_date';
    const endSelect = document.createElement('input');
    endSelect.type = 'date';
    endSelect.id = 'shared_labs_end_date';
    endSelect.min = minDate;
    endSelect.max = maxDate;
    endSelect.value = storedEnd;

    dateRangeCont.appendChild(startLabel);
    dateRangeCont.appendChild(startSelect);
    dateRangeCont.appendChild(endLabel);
    dateRangeCont.appendChild(endSelect);
    controls.appendChild(dateRangeCont);

    // Handle changes
    controls.addEventListener('change', e => {
      if (e.target.type === 'checkbox') {
        renderCharts(el, _labMedEvents);
      } else if (e.target.type === 'date') {
        let start = startSelect.value;
        let end = endSelect.value;
        if (start > end) {
          alert('Start date must be before or equal to end date');
          e.target.value = e.target.id === 'shared_labs_start_date' ? end : start;
          return;
        }
        storageSet('shared_labs_date_start', start);
        storageSet('shared_labs_date_end', end);
        loadAndRender(el, start, end);
      }
    });

    console.log('Rendered controls count:', controls.querySelectorAll('input[type=checkbox]').length);
  }

  function renderCharts(el, medEvents = []) {
    if (!_dataCache) return;

    const checkedMetrics = Array.from(el.querySelectorAll('.hp-labs-controls input[type=checkbox]:checked'))
      .map(cb => cb.value);

    const body = $('.hp-labs-body', el);
    body.innerHTML = '';

    const seriesMap = {};
    _dataCache.forEach(metricData => {
      if (metricData && metricData.metric) seriesMap[metricData.metric] = metricData.series || [];
    });

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

  function dumpCatalogMetrics(catalog) {
    console.log('Catalog dump:');
    catalog.forEach((c) => {
      console.log(`  Metric key: ${c.metric}, Label: ${c.label || '-'}'`);
    });
  }

  // Update loadAndRender to use date filter parameters
  async function loadAndRender(el, startDate, endDate) {
    try {
      const personId = (el && el.dataset && el.dataset.personId) ? el.dataset.personId : 'me';
      const params = new URLSearchParams();
      if (startDate) params.set('start_date', startDate);
      if (endDate) params.set('end_date', endDate);

      const [seriesRes, metaRes, catalogRes] = await Promise.allSettled([
        fetch(`/labs/${encodeURIComponent(personId)}/all-series?` + params.toString(), {cache:'no-store'}).then(r=>r.json()),
        fetch(`/labs/${encodeURIComponent(personId)}/labs-metadata`, {cache:'no-store'}).then(r=>r.json()),
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

      function normalizeKey(str) {
        return str ? str.toLowerCase().trim() : '';
      }

      const filteredMetadata = (meta || []).filter(m => {
        const k = normalizeKey(m.metric);
        return m && m.metric && !VITALS_BLACKLIST.has(k);
      });

      const normalizedCatalog = (catalog || []).map(c => ({
        ...c,
        metric: normalizeKey(c.metric),
        label: c.label ? normalizeKey(c.label) : '',
      }));

      const seriesMetrics = Array.from(new Set(
        series.map(s => s.metric).filter(m => !VITALS_BLACKLIST.has(normalizeKey(m)))
      ));

      const filteredMetaMetrics = filteredMetadata.map(m => normalizeKey(m.metric));

      const supersetMetricsSet = new Set([
        ...normalizedCatalog
          .filter(c => !VITALS_BLACKLIST.has(c.metric))
          .map(c => ALIAS_MAP[c.label] || ALIAS_MAP[c.metric] || c.metric),
        ...filteredMetaMetrics,
        ...seriesMetrics,
        ...Object.keys(CATEGORY_MAP).map(k => normalizeKey(k)),
      ]);

      let metricList = Array.from(supersetMetricsSet);

      if (filteredMetaMetrics.length) {
        metricList.sort((a,b) => {
          const ia = filteredMetaMetrics.indexOf(a);
          const ib = filteredMetaMetrics.indexOf(b);
          if (ia === -1 && ib === -1) return a.localeCompare(b);
          if (ia === -1) return 1;
          if (ib === -1) return -1;
          return ia - ib;
        });
      } else {
        metricList.sort();
      }

      const metaMap = {};
      filteredMetadata.forEach(m => {
        metaMap[normalizeKey(m.metric)] = m;
      });

      normalizedCatalog.forEach(c => {
        const key = ALIAS_MAP[c.label] || ALIAS_MAP[c.metric] || c.metric;
        if (!(key in metaMap) && !VITALS_BLACKLIST.has(key)) {
          metaMap[key] = { metric: key, label: c.label || key };
        }
      });

      Object.entries(CATEGORY_MAP).forEach(([k,v]) => {
        const normK = normalizeKey(k);
        if (!(normK in metaMap)) {
          metaMap[normK] = { metric: normK, label: normK, group: v };
        }
      });

      const initialChecked = metricList.filter(m => seriesMetrics.includes(m)).slice(0, 5);

      const displayMeta = metricList.map(m => {
        const d = metaMap[m] ? Object.assign({}, metaMap[m]) : { metric: m, label: m };
        if (!seriesMetrics.includes(m)) d.disabled = true;
        return d;
      });

      console.log('Filtered and normalized metrics:', metricList);
      console.log('Display metadata:', displayMeta);

      try {
        _labMedEvents = await fetchMedications(personId);
      } catch(e) {
        _labMedEvents = [];
      }

      window.ALL_METRICS = metricList; window._dataCache = _dataCache;

      renderControlsWithGroups(el, displayMeta, initialChecked);
      renderCharts(el, _labMedEvents);
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
