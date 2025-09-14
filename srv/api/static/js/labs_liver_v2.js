(function(){
  'use strict';

  // Import shared utils
  const { $, $$, storageGet, storageSet, parseISODate, getDateRange, makeCheckbox, makeDateSelect} = window.hpLabsShared;
  const { fetchMedications, addMedicationOverlays } = window.hpLabsOverlays;

  const SEL = '.hp-labs-liver';

  const METRIC_LABELS = {
    alt: 'ALT',
    ast: 'AST',
    alp: 'ALP',
    ggt: 'GGT',
    bili_total: 'Bilirubin Total',
    bili_direct: 'Bilirubin Direct',
    albumin: 'Albumin'
  };

  let _dataCache = null;
  let _personId = null;
  let _liverMedEvents = [];

  async function fetchSeries(personId, metrics, startDate, endDate){
    const baseUrl = `/labs/${encodeURIComponent(personId)}/liver-series`;
    const params = new URLSearchParams();
    if(metrics && metrics.length) params.set('metrics', metrics.join(','));
    if(startDate) params.set('start_date', startDate);
    if(endDate) params.set('end_date', endDate);

    const response = await fetch(baseUrl + '?' + params.toString(), {cache:'no-store'});
    if(!response.ok) throw new Error('Failed to load series');
    return response.json();
  }

  function setupUI(el, availableMetrics, initialChecked) {
    const controls = $('.hp-labs-controls', el);
    controls.innerHTML = '';

    if(!_dataCache || _dataCache.length === 0){
      controls.textContent = 'No data available for date range selection';
      return;
    }

    const {minDate, maxDate} = getDateRange(_dataCache);

    const storedStart = storageGet('liver_date_start', minDate.toISOString().slice(0,10));
    const storedEnd = storageGet('liver_date_end', maxDate.toISOString().slice(0,10));

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
        renderCharts(el, _liverMedEvents);
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

  function renderCharts(el, medEvents=[]) {
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
        datasetsMap[m].push({x: point.t_utc, y: point.v});
      });
    });

    const canvas = document.createElement('canvas');
    body.appendChild(canvas);

    const ctx = canvas.getContext('2d');

    const colors = ['#2563eb', '#f97316', '#4ade80', '#f43f5e', '#60a5fa', '#a78bfa', '#fca5a5'];

    const datasets = checkedMetrics.map((m, idx) => ({
      label: METRIC_LABELS[m] || m,
      data: datasetsMap[m],
      borderColor: colors[idx % colors.length],
      fill: false,
      tension: 0.3,
      pointRadius: 2
    }));

    if(window._labsLiverChartInstance) window._labsLiverChartInstance.destroy();

    window._labsLiverChartInstance = new Chart(ctx, {
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

    // Add medication overlays if any
    if(medEvents && medEvents.length > 0){
      addMedicationOverlays(window._labsLiverChartInstance, medEvents, { color:'#f43f5e', label:'Medications' });
    }
  }

  async function loadAndRender(el, startDate, endDate) {
    try {
      _personId = el.getAttribute('data-person-id');
      const metricsAttr = el.getAttribute('data-metrics');
      const metrics = (metricsAttr && metricsAttr.split(',')) || Object.keys(METRIC_LABELS);
      const data = await fetchSeries(_personId, metrics, startDate, endDate);
      _dataCache = data;

      const medEvents = await fetchMedications(_personId);
      _liverMedEvents = medEvents || [];

      setupUI(el, Object.keys(METRIC_LABELS), metrics);
      renderCharts(el, _liverMedEvents);
    } catch (e) {
      console.warn('Error loading liver panel:', e);
    }
  }

  window.labsLiverPanel = { loadAndRender };

  function boot() {
    document.querySelectorAll(SEL).forEach(el => loadAndRender(el));
  }

  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

})();
