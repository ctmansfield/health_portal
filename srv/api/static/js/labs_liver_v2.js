(function(){
  'use strict';

  // Import shared utils
  const { $, $$, storageGet, storageSet, parseISODate, getDateRange, makeCheckbox, makeDateSelect} = window.hpLabsShared;
  const { fetchMedications } = window.hpLabsOverlays;

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
        const medToggle = $('#medication-overlay-toggle-liver');
        const showMedOverlay = medToggle ? medToggle.checked : true;
        renderCharts(el, showMedOverlay ? _liverMedEvents : []);
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

  // Helper to create medication overlay plugin with color and label
  function makeMedOverlayPlugin(medEvents, options = {}) {
    // Map medication name patterns to colors
    const defaultColor = 'rgba(244,63,94,0.4)'; // default light red transparent
    const colors = {
      testosterone: 'rgba(74,222,128,0.4)', // light green transparent
      lisinopril: 'rgba(244,63,94,0.4)', // light red transparent
    };

    return {
      id: 'medOverlay',
      medEvents,
      afterDraw(chart) {
        const ctx = chart.ctx;
        const yAxis = chart.scales.y;
        medEvents.forEach(event => {
          if (!event.time) return;
          const xScale = chart.scales.x;
          const x = xScale.getPixelForValue(event.time);
          ctx.save();
          // Choose color based on med name matching
          let color = defaultColor;
          const labelLower = (event.label || '').toLowerCase();
          if(labelLower.includes('testosterone')) color = colors.testosterone;
          else if(labelLower.includes('lisinopril')) color = colors.lisinopril;

          ctx.strokeStyle = color.replace(/,0\.4\)/, ',0.8)'); // darker stroke
          ctx.fillStyle = color;
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(x, yAxis.top);
          ctx.lineTo(x, yAxis.bottom);
          ctx.stroke();
          ctx.font = '10px Arial';
          ctx.fillText(event.label || '', x + 4, yAxis.top + 10);
          ctx.restore();
        });
      }
    };
  }

  function renderCharts(el, medEvents = []) {
    if (!_dataCache) return;

    const checkedMetrics = Array.from(el.querySelectorAll('.hp-labs-controls input[type=checkbox]:checked'))
      .map(cb => cb.value);
    const body = $('.hp-labs-body', el);
    body.innerHTML = '';

    const datasetsMap = {};
    checkedMetrics.forEach(m => datasetsMap[m] = []);

    _dataCache.forEach(metricData => {
      const m = metricData.metric;
      if (!datasetsMap[m]) return;
      metricData.series.forEach(point => {
        datasetsMap[m].push({ x: point.t_utc, y: point.v });
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

    if (window._labsLiverChartInstance) window._labsLiverChartInstance.destroy();

    const plugins = [];
    if (medEvents.length > 0) {
      plugins.push(makeMedOverlayPlugin(medEvents, { color: '#f43f5e', label: 'Medications' }));
    }

    window._labsLiverChartInstance = new Chart(ctx, {
      type: 'line',
      data: { datasets },
      options: {
        responsive: true,
        parsing: { xAxisKey: 'x', yAxisKey: 'y' },
        scales: {
          x: { type: 'time', time: { unit: 'day' }, title: { display: true, text: 'Date' } },
          y: { title: { display: true, text: 'Value' } }
        },
        plugins: { legend: { display: true } }
      },
      plugins // Chart.js v3+ allows plugins array here
    });
  }

  function createMedToggle(el, initialState = true) {
    const container = $('.hp-labs-controls', el);
    if (!container) return;
    const toggleLabel = document.createElement('label');
    toggleLabel.style.marginTop = '8px';
    toggleLabel.style.cursor = 'pointer';

    const toggle = document.createElement('input');
    toggle.type = 'checkbox';
    toggle.checked = initialState;
    toggle.style.marginRight = '6px';
    toggle.id = 'medication-overlay-toggle-liver';

    toggleLabel.appendChild(toggle);
    toggleLabel.appendChild(document.createTextNode('Show Medication Overlays'));

    container.appendChild(toggleLabel);

    toggle.addEventListener('change', () => {
      renderCharts(el, toggle.checked ? _liverMedEvents : []);
    });

    return toggle;
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

      // Add medication overlay toggle
      createMedToggle(el, true);
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
