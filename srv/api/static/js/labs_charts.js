(function(){
  'use strict';

  function inferUnits(metric, series){
    const vals = (series||[]).map(p => (p && p.v != null) ? Number(p.v) : null).filter(v => v != null && !Number.isNaN(v));
    const avg = vals.length ? vals.reduce((a,b)=>a+b,0)/vals.length : 0;
    if (metric.toLowerCase().includes('spo2') || (avg > 0 && avg <= 2)) return '%';
    if (metric.toLowerCase().includes('hr') || metric.toLowerCase().includes('heart')) return 'bpm';
    return '';
  }

  function renderCharts(el, series, overlays){
    const body = el.querySelector('.hp-labs-body');
    if (!body) return;
    body.innerHTML = '';

    const seriesMap = {}; // metric -> series
    (series || []).forEach(md => { if (md && md.metric) seriesMap[md.metric.toLowerCase()] = md.series || []; });

    const selected = Array.from(el.querySelectorAll('.hp-labs-controls input[type=checkbox]:checked')).map(cb => cb.value.toLowerCase());

    if (selected.length === 0) return;

    const metricsByPanel = { 'Selected': selected };

    Object.entries(metricsByPanel).forEach(([panelName, metrics]) => {
      const panelDiv = document.createElement('div');
      panelDiv.className = 'hp-labs-chart-panel';

      const header = document.createElement('h2');
      header.textContent = panelName + ' Panel';
      panelDiv.appendChild(header);

      const canvas = document.createElement('canvas');
      panelDiv.appendChild(canvas);
      body.appendChild(panelDiv);

      const datasets = [];
      const unitToAxis = {};
      let axisCount = 0;

      metrics.forEach((m, idx) => {
        // Ensure chronological order to prevent lines from "looping back"
        const s = (seriesMap[m] || []).slice().sort((a,b) => {
          const da = new Date(a.t_utc); const db = new Date(b.t_utc);
          return da - db;
        });
        const unit = inferUnits(m, s);
        const axisId = unitToAxis[unit] || (unitToAxis[unit] = (axisCount++ === 0 ? 'y' : 'y' + axisCount));
        datasets.push({
          label: m + (unit ? ` (${unit})` : ''),
          data: s.map(p => ({ x: p.t_utc, y: (p.v != null ? Number(p.v) : null) })),
          borderColor: ['#2563eb','#f97316','#4ade80','#f43f5e','#60a5fa','#a78bfa','#fca5a5','#84cc16','#22d3ee','#fbbf24'][idx % 10],
          backgroundColor: ['#2563eb','#f97316','#4ade80','#f43f5e','#60a5fa','#a78bfa','#fca5a5','#84cc16','#22d3ee','#fbbf24'][idx % 10],
          fill: false,
          stepped: false,
          tension: 0.3,
          pointRadius: 1.5,
          spanGaps: true,
          yAxisID: axisId
        });
      });

      const scales = { x: { type: 'time', time: { unit: 'day', tooltipFormat: 'yyyy-MM-dd HH:mm' }, adapters: {}, title: { display: true, text: 'Date' } } };
      const primaryUnit = Object.keys(unitToAxis)[0] || '';
      scales['y'] = { position: 'left', title: { display: true, text: primaryUnit || 'Value' }, grid: { drawOnChartArea: true } };
      for (const [u, axisId] of Object.entries(unitToAxis)) {
        if (axisId === 'y') continue;
        scales[axisId] = { position: 'right', title: { display: !!u, text: u || '' }, grid: { drawOnChartArea: false }, offset: true };
      }

      const ctx = canvas.getContext('2d');
      const chart = new Chart(ctx, {
        type: 'line', data: { datasets }, options: {
          responsive: true,
          parsing: { xAxisKey: 'x', yAxisKey: 'y' },
          normalized: true,
          scales,
          plugins: {
            legend: { display: true },
            tooltip: { 
              mode: 'nearest', 
              intersect: false,
              callbacks: {
                label: function(ctx){
                  const v = ctx.formattedValue;
                  return `${ctx.dataset.label}: ${v}`;
                }
              }
            },
            zoom: { pan: { enabled: true, mode: 'x' }, zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: 'x' } }
          }
        }
      });

      if (overlays && overlays.length && window.hpLabsOverlays && window.hpLabsOverlays.addMedicationOverlays) {
        try { window.hpLabsOverlays.addMedicationOverlays(chart, overlays); } catch(e) { console.warn('med overlays failed', e); }
      }
    });
  }

  window.hpLabsCharts = { renderCharts };
})();
