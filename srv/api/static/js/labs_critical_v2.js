(function(){
  'use strict';

  // Import shared utils
  const { $, $$, storageGet, storageSet, parseISODate, getDateRange, makeCheckbox, makeDateSelect } = window.hpLabsShared;

  // After shared utils import, import overlays
  const { fetchMedications } = window.hpLabsOverlays;

  const SEL = '.hp-labs-critical';

  const METRIC_LABELS = {
    hr: 'Heart Rate',
    spo2: 'SpO2'
  };

  let _dataCache = null;
  let _personId = null;

  // Add global caches
  let _criticalMedEvents = [];

  // Add test medication events for overlay testing
  const TEST_MED_EVENTS = [
    { time: '2023-12-06T00:00:00Z', label: 'Testosterone 150mg/week' },
    { time: '2022-02-26T00:00:00Z', label: 'Lisinopril 10mg' },
    { time: '2022-04-14T00:00:00Z', label: 'Lisinopril 20mg' },
    { time: '2023-06-15T00:00:00Z', label: 'Lisinopril 80mg daily' },
    { time: '2024-07-01T00:00:00Z', label: 'Lisinopril discontinued' },
    { time: '2025-03-06T00:00:00Z', label: 'Lisinopril resumed 40mg daily' },
    { time: '2025-05-06T00:00:00Z', label: 'Lisinopril stopped' }
  ];

  async function fetchSeries(personId, metrics, startDate, endDate){
    const baseUrl = `/labs/${encodeURIComponent(personId)}/critical-series`;
    const params = new URLSearchParams();
    if(metrics && metrics.length) params.set('metrics', metrics.join(','));
    if(startDate) params.set('start_date', startDate);
    if(endDate) params.set('end_date', endDate);

    const response = await fetch(baseUrl + '?' + params.toString(), {cache:'no-store'});
    if(!response.ok) throw new Error('Failed to load critical series');
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

    const startFallback = minDate instanceof Date && !isNaN(minDate) ? minDate.toISOString().slice(0,10) : new Date().toISOString().slice(0,10);
    const endFallback = maxDate instanceof Date && !isNaN(maxDate) ? maxDate.toISOString().slice(0,10) : new Date().toISOString().slice(0,10);
    const storedStart = storageGet('critical_date_start', startFallback);
    const storedEnd = storageGet('critical_date_end', endFallback);

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

    const startSelect = makeDateSelect('critical_start_date', 'Start Date', storedStart, minDate, maxDate);
    const endSelect = makeDateSelect('critical_end_date', 'End Date', storedEnd, minDate, maxDate);

    dateRangeContainer.appendChild(startSelect);
    dateRangeContainer.appendChild(endSelect);

    controls.appendChild(boxList);
    controls.appendChild(dateRangeContainer);

    controls.addEventListener('change', e => {
      if(e.target.tagName === 'INPUT' && e.target.type === 'checkbox' && e.target.id !== 'medication-overlay-toggle') {
        const medToggle = $('#medication-overlay-toggle', el);
        renderCharts(el, medToggle && medToggle.checked ? _criticalMedEvents : []);
      } else if(e.target.tagName === 'SELECT') {
        const start = $('#critical_start_date').value;
        const end = $('#critical_end_date').value;
        if(start > end){
          alert('Start date must be before or equal to end date.');
          if(e.target.id === 'critical_start_date') e.target.value = end;
          else e.target.value = start;
          return;
        }
        storageSet('critical_date_start', start);
        storageSet('critical_date_end', end);
        loadAndRender(el, start, end);
      }
    });
  }

  function makeMedOverlayPlugin(medEvents, options = {}) {
    const { color = '#4ade80', label = 'Medications' } = options;

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
          ctx.strokeStyle = color;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(x, yAxis.top);
          ctx.lineTo(x, yAxis.bottom);
          ctx.stroke();
          ctx.fillStyle = color;
          ctx.font = '10px Arial';
          ctx.fillText(event.label||'', x + 4, yAxis.top + 10);
          ctx.restore();
        });
      }
    };
  }

  function renderCharts(el, medEvents = []) {
    if (!_dataCache) return;
    const checkedMetrics = Array.from(el.querySelectorAll('.hp-labs-controls input[type=checkbox]:checked')).filter(cb => cb.id !== 'medication-overlay-toggle').map(cb => cb.value);
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

    const colors = ['#2563eb', '#4ade80'];

    const datasets = checkedMetrics.map((m, idx) => ({
      label: METRIC_LABELS[m] || m,
      data: datasetsMap[m],
      borderColor: colors[idx % colors.length],
      fill: false,
      tension: 0.3,
      pointRadius: 2
    }));

    if (window._labsCriticalChartInstance) window._labsCriticalChartInstance.destroy();

    const plugins = [];
    if (medEvents.length > 0) {
      plugins.push(makeMedOverlayPlugin(medEvents, { color: '#4ade80', label: 'Medications' }));
    }

    window._labsCriticalChartInstance = new Chart(ctx, {
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
        plugins // inject medication overlay plugin
      },
      plugins
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
    toggle.id = 'medication-overlay-toggle';

    toggleLabel.appendChild(toggle);
    toggleLabel.appendChild(document.createTextNode('Show Medication Overlays'));

    container.appendChild(toggleLabel);

    toggle.addEventListener('change', () => {
      renderCharts(el, toggle.checked ? _criticalMedEvents : []);
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
      const mergedEvents = [...medEvents, ...TEST_MED_EVENTS];

      // Filter valid med events
      const validMedEvents = mergedEvents.filter(e => e && typeof e.time === 'string' && typeof e.label === 'string');
      _criticalMedEvents = validMedEvents;

      setupUI(el, Object.keys(METRIC_LABELS), metrics);

      renderCharts(el, validMedEvents);

      // Create medication overlay toggle
      createMedToggle(el, true);

    } catch (e) {
      console.warn('Error loading critical panel:', e);
    }
  }

  window.labsCriticalPanel = { loadAndRender };

  function boot() {
    document.querySelectorAll(SEL).forEach(el => loadAndRender(el));
  }

  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
