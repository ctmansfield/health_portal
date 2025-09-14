(function(){
  'use strict';

  const SEL = '.hp-labs-liver';
  const $ = (sel, el=document) => el.querySelector(sel);

  // Liver metrics known keys and friendly labels
  const METRIC_LABELS = {
    alt: 'ALT',
    ast: 'AST',
    alp: 'ALP',
    ggt: 'GGT',
    bili_total: 'Bilirubin Total',
    bili_direct: 'Bilirubin Direct',
    albumin: 'Albumin'
  };

  // Demo data for isolated frontend testing
  const DEMO_LIVER_DATA = [
    { metric: 'alt', unit: '', tz: 'UTC', series: [
      { t_utc: '2025-09-01', v: 40 }, { t_utc: '2025-09-02', v: 42 }, { t_utc: '2025-09-03', v: 38 }
    ]},
    { metric: 'ast', unit: '', tz: 'UTC', series: [
      { t_utc: '2025-09-01', v: 35 }, { t_utc: '2025-09-02', v: 37 }, { t_utc: '2025-09-03', v: 34 }
    ]}
  ];

  // Utility to parse ISO date strings
  function parseISODate(s){ return new Date(s); }

  // Utility to find earliest and latest dates over all series
  function getDateRange(data) {
    let minDate = null, maxDate = null;
    if (!data || data.length === 0) {
      const today = new Date();
      minDate = new Date(today.getFullYear(), today.getMonth(), today.getDate());
      maxDate = new Date(minDate);
      console.log('getDateRange: empty data fallback to today', minDate, maxDate);
      return { minDate, maxDate };
    }
    data.forEach(series => {
      console.log('Series for metric:', series.metric);
      if (!series.series) {
        console.warn('Series missing in metric', series.metric);
        return;
      }
      series.series.forEach(p => {
        console.log('Data point:', p);
        const d = parseISODate(p.t_utc);
        if (!minDate || d < minDate) minDate = d;
        if (!maxDate || d > maxDate) maxDate = d;
      });
    });
    console.log('getDateRange:', minDate, maxDate);
    return { minDate, maxDate };
  }

  // Simple localStorage helpers
  function storageGet(k,d){ try{ const v=localStorage.getItem(k); return v==null? d : v; }catch(e){ return d; } }
  function storageSet(k,v){ try{ localStorage.setItem(k,String(v)); }catch(e){} }

  async function fetchLiverSeries(personId, metrics, startDate, endDate){
    const baseUrl = `/labs/${encodeURIComponent(personId)}/liver-series`;
    const params = new URLSearchParams();
    if(metrics && metrics.length) params.set('metrics', metrics.join(','));
    if(startDate) params.set('start_date', startDate);
    if(endDate) params.set('end_date', endDate);
    const response = await fetch(baseUrl + '?' + params.toString(), {cache:'no-store'});
    if(!response.ok) throw new Error('Failed to load liver series');
    return response.json();
  }

  function makeCheckbox(metricKey, label, checked=true){
    const container = document.createElement('div');
    container.style.marginBottom = '6px';
    const cb = document.createElement('input');
    cb.type = 'checkbox'; cb.id = 'cb_' + metricKey; cb.value = metricKey; cb.checked = checked;
    const lbl = document.createElement('label');
    lbl.htmlFor = cb.id;
    lbl.textContent = label;
    lbl.style.marginLeft = '6px';
    container.appendChild(cb); container.appendChild(lbl);
    return container;
  }

  function makeDateSelect(id, label, date, minDate, maxDate){
    const container = document.createElement('div');
    container.style.marginRight = '12px';
    const lbl = document.createElement('label');
    lbl.htmlFor = id;
    lbl.textContent = label + ': ';
    lbl.style.marginRight = '4px';
    const select = document.createElement('select');
    select.id = id;

    for(let d = new Date(minDate); d <= maxDate; d.setDate(d.getDate() + 1)){
      const option = document.createElement('option');
      option.value = d.toISOString().slice(0,10);
      option.textContent = d.toISOString().slice(0,10);
      if(option.value === date) option.selected = true;
      select.appendChild(option);
    }
    container.appendChild(lbl);
    container.appendChild(select);
    return container;
  }

  function setupUI(el, availableMetrics, initialChecked) {
    const controls = $('.hp-labs-controls', el);
    controls.innerHTML = '';

    if(!_liverDataCache || _liverDataCache.length === 0){
      controls.textContent = 'No data available for date range selection';
          return;
    }

    const {minDate, maxDate} = getDateRange(_liverDataCache);

    if(!minDate || !maxDate) {
      controls.textContent = 'Date range data is not available';
          return;
    }
    const storedStartRaw = storageGet('liver_date_start', null);
    const storedEndRaw = storageGet('liver_date_end', null);

    const storedStart = storedStartRaw ? storedStartRaw : minDate.toISOString().slice(0,10);
    const storedEnd = storedEndRaw ? storedEndRaw : maxDate.toISOString().slice(0,10);

    const boxList = document.createElement('div');
    boxList.style.display = 'flex';
    boxList.style.flexDirection = 'column';
    boxList.style.marginRight = '24px';

    availableMetrics.forEach(m => {
      const cb = makeCheckbox(m, METRIC_LABELS[m]||m, initialChecked.includes(m));
      boxList.appendChild(cb);
    });

    const dateRangeContainer = document.createElement('div');
    dateRangeContainer.style.display = 'flex';
    dateRangeContainer.style.alignItems = 'center';

    const startSelect = makeDateSelect('liver_start_date', 'Start Date', storedStart, minDate, maxDate);
    const endSelect = makeDateSelect('liver_end_date', 'End Date', storedEnd, minDate, maxDate);

    dateRangeContainer.appendChild(startSelect);
    dateRangeContainer.appendChild(endSelect);

    controls.appendChild(boxList);
    controls.appendChild(dateRangeContainer);

    controls.addEventListener('change', e => {
      if(e.target.tagName === 'INPUT' && e.target.type === 'checkbox') {
      renderCharts(el);
      } else if(e.target.tagName === 'SELECT') {
        const start = $('#liver_start_date').value;
        const end = $('#liver_end_date').value;
        if(start > end){
          alert('Start date must be before or equal to end date.');
          if(e.target.id === 'liver_start_date') e.target.value = end;
          else e.target.value = start;
          return;
    }
        storageSet('liver_date_start', start);
        storageSet('liver_date_end', end);
        loadAndRender(el, start, end);
  }
    });
  }

  // Globals for state
  let _liverDataCache = null;
  let _personId = null;
  function renderCharts(el) {
    if(!_liverDataCache) return;
    const checkedMetrics = Array.from(el.querySelectorAll('.hp-labs-controls input[type=checkbox]:checked'))
      .map(cb => cb.value);

    const start = $('#liver_start_date') ? $('#liver_start_date').value : null;
    const end = $('#liver_end_date') ? $('#liver_end_date').value : null;
    const startDate = start ? new Date(start+'T00:00:00Z') : null;
    const endDate = end ? new Date(end+'T23:59:59Z') : null;

    const body = $('.hp-labs-body', el);
    body.innerHTML = '';

    const datasetsMap = {};
    checkedMetrics.forEach(m => datasetsMap[m] = []);

    _liverDataCache.forEach(metricData => {
      const m = metricData.metric;
      if(!datasetsMap[m]) return;
      metricData.series.forEach(point => {
        // Filter by range
        const d = new Date(point.t_utc);
        if(startDate && d < startDate) return;
        if(endDate && d > endDate) return;
        datasetsMap[m].push({x: point.t_utc, y: point.v});
    });
    });

    // Create canvas
    const canvas = document.createElement('canvas');
    body.appendChild(canvas);

    const ctx = canvas.getContext('2d');

    // Plot using Chart.js
    const datasets = checkedMetrics.map((m, idx) => ({
      label: METRIC_LABELS[m] || m,
      data: datasetsMap[m],
      borderColor: [`#2563eb`, `#f97316`, `#4ade80`, `#f43f5e`, `#60a5fa`, `#a78bfa`, `#fca5a5`][idx % 7],
      fill: false,
      tension: 0.3,
      pointRadius: 2
    }));

    if(window._liverChartInstance) window._liverChartInstance.destroy();

    window._liverChartInstance = new Chart(ctx, {
      type: 'line',
      data: {datasets: datasets},
      options: {
        responsive: true,
        parsing: {xAxisKey: 'x', yAxisKey: 'y'},
        scales: {
          x: {type: 'time', time: {unit: 'day'}, title: {display:true, text:'Date'}},
          y: {title: {display:true, text:'Value'}}
        },
        plugins: {legend: {display: true}}
      }
    });
  }

  async function loadAndRender(el, startDate, endDate) {
    try {
      _personId = el.getAttribute('data-person-id');
      const metricsAttr = el.getAttribute('data-metrics');
      const metrics = (metricsAttr && metricsAttr.split(',')) || Object.keys(METRIC_LABELS);

      const useDemo = false; // Set true to force demo data for testing
      let data;
      if(useDemo) {
        console.log('Using demo liver data for testing');
        data = DEMO_LIVER_DATA;
      } else {
        data = await fetchLiverSeries(_personId, metrics, startDate, endDate);
      }

      console.log('Loaded liver data:', data);
      _liverDataCache = data;
      setupUI(el, Object.keys(METRIC_LABELS), metrics);
      renderCharts(el);
    } catch (e) {
      console.warn('Error loading liver panel:', e);
    }
  }

  function boot() {
    document.querySelectorAll(SEL).forEach(el => {
      const storedStart = storageGet('liver_date_start', null);
      const storedEnd = storageGet('liver_date_end', null);
      loadAndRender(el, storedStart, storedEnd);
    });
  }

  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

})();
