// srv/api/static/js/labs_critical_v2.js
// Clean, defensive Labs UI client (ref bands, legend, export)
// Paste the entire block below into the target file in one operation.
(function(){
  'use strict';

  const SEL = '.hp-labs-critical';
  const $ = (s, el=document) => el.querySelector(s);

  function escapeHtml(s){ return String(s).replace(/[&<>"']/g, ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[ch]); }
  function canonicalMetric(m){ try{ return String(m||'').toLowerCase().replace(/[^a-z0-9]/g,''); }catch(e){ return String(m||''); } }
  function downsample(arr, maxPoints=2000){ if(!Array.isArray(arr)) return arr; const n=arr.length; if(n<=maxPoints) return arr.slice(); const step=Math.ceil(n/maxPoints); return arr.filter((_,i)=> i % step === 0); }
  function storageGet(k,d){ try{ const v=localStorage.getItem(k); return v==null? d : v; }catch(e){ return d; } }
  function storageSet(k,v){ try{ localStorage.setItem(k,String(v)); }catch(e){} }

  const REF_BANDS = {
    hr:   [{label:'Normal', min:60, max:100}],
    spo2: [{label:'Healthy', min:94, max:100}]
  };

  function _downloadCSV(metric, series){
    try{
      const rows = [['t_utc','t_local','value']];
      (series||[]).forEach(p => rows.push([p.t_utc||p.t||'', p.t_local||'', p.v==null ? '' : String(p.v)]));
      const csv = rows.map(r=> r.map(c=> '"' + String(c).replace(/"/g,'""') + '"').join(',')).join('\n');
      const blob = new Blob([csv], {type:'text/csv'});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url;
      a.download = metric.replace(/[^a-z0-9]/gi,'_') + '_series.csv';
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    }catch(e){ console.warn('downloadCSV error', e); }
  }

  const CHARTS = [];
  const PREVIEW = { key:null, data:null, ts:0, inflight:null, ttl:30000 };

  async function fetchPreview(person){
    const key = String(person||'');
    const now = Date.now();
    if(PREVIEW.key === key && PREVIEW.data && (now - PREVIEW.ts) < PREVIEW.ttl) return PREVIEW.data;
    if(PREVIEW.inflight){ try{return await PREVIEW.inflight;}catch(e){return null;} }
    PREVIEW.inflight = (async ()=>{
      try{
        const res = await fetch('/ui/preview/labs/' + encodeURIComponent(key), {cache:'no-store'});
        if(!res.ok) return null;
        const j = await res.json();
        PREVIEW.key = key; PREVIEW.data = j; PREVIEW.ts = Date.now();
        return j;
      }catch(e){ console.warn('preview fetch error', e); return null; } finally { PREVIEW.inflight = null; }
    })();
    try{ return await PREVIEW.inflight; }catch(e){ return null; }
  }

  function attachInteractions(meta){
    const canvas = meta.canvas;
    const parent = canvas.parentElement;
    parent.style.position = parent.style.position || 'relative';

    const overlay = document.createElement('div');
    overlay.style.position = 'absolute';
    overlay.style.pointerEvents = 'none';
    overlay.style.display = 'none';
    overlay.style.top = '0'; overlay.style.left = '0'; overlay.style.height = '100%';
    overlay.style.zIndex = 5; overlay.style.boxSizing = 'border-box';
    overlay.style.background = 'rgba(37,99,235,0.12)';
    overlay.style.border = '1px dashed rgba(37,99,235,0.4)';
    parent.appendChild(overlay);
    meta.overlay = overlay;

    let dragging=false, sx=0, ex=0;
    function timeAt(x){
      const r = canvas.getBoundingClientRect();
      const rel = Math.max(0, Math.min(1, (x - r.left) / r.width));
      const idx = Math.floor(rel * (meta.labels.length - 1));
      return meta.labels[Math.max(0, Math.min(meta.labels.length - 1, idx))];
    }

    meta.handlers = {};
    meta.handlers.down = e => {
      if(e.button !== 0) return;
      dragging = true; sx = e.clientX; ex = sx;
      overlay.style.display = 'block';
      const r = canvas.getBoundingClientRect(); overlay.style.left = (sx - r.left) + 'px'; overlay.style.width = '0px';
      try{ canvas.setPointerCapture(e.pointerId); }catch(_){}
    };
    meta.handlers.move = e => {
      if(!dragging) return;
      ex = e.clientX;
      const r = canvas.getBoundingClientRect();
      const l = Math.min(sx, ex), rg = Math.max(sx, ex);
      overlay.style.left = Math.max(0, l - r.left) + 'px';
      overlay.style.width = Math.max(2, rg - l) + 'px';
      overlay.style.height = r.height + 'px';
    };
    meta.handlers.up = e => {
      if(!dragging) return;
      dragging = false; overlay.style.display = 'none';
      try{ canvas.releasePointerCapture(e.pointerId); }catch(_){}
      const t1 = timeAt(sx), t2 = timeAt(ex);
      if(t1 && t2 && t1 !== t2){ const s = t1 < t2 ? t1 : t2, ee = t1 < t2 ? t2 : t1; applyViewWindowToAll(s, ee); }
    };
    meta.handlers.dbl = () => resetAllViews();
    meta.handlers.wheel = ev => {
      if(!ev.shiftKey) return;
      ev.preventDefault();
      const labels = meta.labels; const len = labels.length; if(len <= 1) return;
      const curS = meta.viewStart == null ? 0 : meta.viewStart;
      const curE = meta.viewEnd == null ? len-1 : meta.viewEnd;
      const win = curE - curS + 1; const step = Math.max(1, Math.floor(win * 0.15));
      const delta = ev.deltaY > 0 ? 1 : -1; let ns = curS + delta * step, ne = curE + delta * step;
      if(ns < 0){ ns = 0; ne = Math.min(len-1, ns + win -1); } if(ne > len-1){ ne = len-1; ns = Math.max(0, ne - win +1); }
      applyViewWindowToAll(labels[ns], labels[ne]);
    };

    canvas.addEventListener('pointerdown', meta.handlers.down);
    canvas.addEventListener('pointermove', meta.handlers.move);
    canvas.addEventListener('pointerup', meta.handlers.up);
    canvas.addEventListener('dblclick', meta.handlers.dbl);
    canvas.addEventListener('wheel', meta.handlers.wheel, {passive:false});
  }

  function createChart(canvas, metric, labels, vals, rawSeries, agg){
    try{
      const metricKey = canonicalMetric(metric);
      const dataHash = JSON.stringify(labels).length + ':' + JSON.stringify(vals).length + ':' + JSON.stringify(rawSeries||[]).length;
      if(canvas._hp_hash === dataHash && canvas._hp_chart) return canvas._hp_meta;

      try{ if(canvas._hp_chart && typeof canvas._hp_chart.destroy === 'function') canvas._hp_chart.destroy(); }catch(_){}

      const parent = canvas.parentElement || canvas;
      const cssW = parent.clientWidth || 600, cssH = 160;
      const dpr = window.devicePixelRatio || 1;
      canvas.style.width = cssW + 'px'; canvas.style.height = cssH + 'px';
      canvas.width = Math.max(1, Math.floor(cssW * dpr)); canvas.height = Math.max(1, Math.floor(cssH * dpr));
      const ctx = canvas.getContext('2d'); ctx.setTransform(dpr,0,0,dpr,0,0);

      const refPlugin = {
        id: 'hp_ref_bands',
        beforeDatasetsDraw(chart){
          try{
            const bands = chart.config._refBands;
            if(!bands || !Array.isArray(bands)) return;
            const yScale = chart.scales.y, area = chart.chartArea, ctx = chart.ctx;
            bands.forEach(b => {
              if(b.min == null || b.max == null) return;
              const y1 = yScale.getPixelForValue(b.max), y2 = yScale.getPixelForValue(b.min);
              ctx.save(); ctx.fillStyle = 'rgba(34,197,94,0.08)'; ctx.fillRect(area.left, y1, area.right-area.left, Math.max(1, y2-y1)); ctx.restore();
            });
          }catch(e){}
        }
      };

      const cfg = {
        type: 'line',
        data: { labels: labels.slice(), datasets: [{ label: metric, data: vals.slice(), borderColor:'#2563eb', tension:0.2, pointRadius:1, fill:false }] },
        options: { responsive:false, maintainAspectRatio:false, plugins:{legend:{display:false}}, interaction:{intersect:false}, scales:{ x:{display:true}, y:{beginAtZero:false} } },
        plugins: [refPlugin]
      };

      const storedBands = storageGet('hp_bands_enabled','true') === 'true';
      const bandsToggleEl = document.querySelector('.hp-bands-toggle');
      const uiOn = bandsToggleEl && bandsToggleEl.getAttribute && bandsToggleEl.getAttribute('aria-pressed') === 'true';
      const bandsOn = uiOn || storedBands;
      if(bandsOn && REF_BANDS[metricKey]) cfg._refBands = REF_BANDS[metricKey];

      const chart = new Chart(ctx, cfg);
      canvas._hp_chart = chart; canvas._hp_hash = dataHash;

      const meta = { canvas, chart, metric, metricKey, labels: labels.slice(), vals: vals.slice(), rawSeries: rawSeries? rawSeries.slice():[], agg: agg||'daily', overlay:null, handlers:{}, origPointRadius: (cfg.data && cfg.data.datasets && cfg.data.datasets[0] && cfg.data.datasets[0].pointRadius) || 1 };
      canvas._hp_meta = meta;

      attachInteractions(meta);

      try{
        const root = (canvas.parentElement || document).querySelector('.hp-legend');
        if(root){
          root.innerHTML = '';
          const li = document.createElement('div'); li.setAttribute('role','listitem');
          const btn = document.createElement('button'); btn.type='button'; btn.className='hp-legend-toggle';
          btn.setAttribute('data-series', meta.metricKey);
          const vis = storageGet('hp_series_visible.'+meta.metricKey,'true') === 'true';
          btn.setAttribute('aria-pressed', vis ? 'true' : 'false');
          btn.textContent = metric;
          btn.style.padding='4px 8px'; btn.style.borderRadius='6px'; btn.style.border='1px solid #e6eef8';
          btn.style.background = vis ? '#eefbf3' : '#fff'; btn.style.cursor='pointer';

          btn.addEventListener('click', function(ev){
            if(ev.altKey){
              try{ const ds = meta.chart.data.datasets[0]; if(ds.pointRadius && ds.pointRadius > 0) ds.pointRadius = 0; else ds.pointRadius = meta.origPointRadius || 1; meta.chart.update(); }catch(e){} return;
            }
            const cur = btn.getAttribute('aria-pressed') === 'true';
            const next = !cur; btn.setAttribute('aria-pressed', next ? 'true' : 'false');
            storageSet('hp_series_visible.'+meta.metricKey, next);
            try{ meta.chart.data.datasets[0].hidden = !next; meta.chart.update(); }catch(e){}
            btn.style.background = next ? '#eefbf3' : '#fff';
          });
          btn.addEventListener('keydown', ev => { if(ev.key === 'Enter' || ev.key === ' '){ ev.preventDefault(); btn.click(); } });

          li.appendChild(btn); root.appendChild(li);
          try{ meta.chart.data.datasets[0].hidden = !(storageGet('hp_series_visible.'+meta.metricKey,'true') === 'true'); meta.chart.update(); }catch(e){}
        }
      }catch(e){}

      CHARTS.push(meta);
      console.debug('labs_critical_v2: created chart for', metric);
      return meta;
    }catch(e){ console.warn('createChart exception', e); return null; }
  }

  function destroyMeta(meta){
    if(!meta) return;
    try{ if(meta.chart && typeof meta.chart.destroy==='function') meta.chart.destroy(); }catch(e){}
    try{ if(meta.overlay && meta.overlay.parentElement) meta.overlay.parentElement.removeChild(meta.overlay); }catch(e){}
    try{
      const c = meta.canvas;
      if(c){
        if(meta.handlers && meta.handlers.down) c.removeEventListener('pointerdown', meta.handlers.down);
        if(meta.handlers && meta.handlers.move) c.removeEventListener('pointermove', meta.handlers.move);
        if(meta.handlers && meta.handlers.up) c.removeEventListener('pointerup', meta.handlers.up);
        if(meta.handlers && meta.handlers.dbl) c.removeEventListener('dblclick', meta.handlers.dbl);
        if(meta.handlers && meta.handlers.wheel) c.removeEventListener('wheel', meta.handlers.wheel);
      }
    }catch(e){}
  }

  function applyViewWindowToAll(startTime, endTime){
    if(!startTime || !endTime) return;
    CHARTS.forEach(meta=>{
      const labels = meta.labels;
      const idxStart = labels.findIndex(l => l >= startTime);
      let idxEnd = labels.map((l,i)=>i).reverse().find(i=> labels[i] <= endTime);
      if(idxStart === -1 || idxEnd === undefined || idxEnd < idxStart){
        meta.chart.data.labels = meta.labels.slice();
        meta.chart.data.datasets[0].data = meta.vals.slice();
      } else {
        meta.chart.data.labels = meta.labels.slice(idxStart, idxEnd+1);
        meta.chart.data.datasets[0].data = meta.vals.slice(idxStart, idxEnd+1);
      }
      try{ meta.chart.update(); }catch(e){}
    });
  }

  function resetAllViews(){
    CHARTS.forEach(meta=>{
      try{
        meta.chart.data.labels = meta.labels.slice();
        meta.chart.data.datasets[0].data = meta.vals.slice();
        meta.chart.update();
      }catch(e){}
    });
  }

  function renderCharts(el, data){
    try{
      if(el._lastRender && (Date.now() - el._lastRender) < 300) return;
      el._lastRender = Date.now();
      while(CHARTS.length){ const m = CHARTS.pop(); try{ destroyMeta(m); }catch(e){} }
      const body = $('.hp-labs-body', el); if(!body) return;
      body.innerHTML = '';
      const row = document.createElement('div'); row.className = 'hp-labs-row';
      (data||[]).forEach(m=>{
        const ctn = (function(){ try{ return makeChartContainer(m.metric); }catch(e){ const d=document.createElement('div'); d.textContent = 'error'; return d; } })();
        const canvas = ctn.querySelector && ctn.querySelector('canvas');
        const btn = ctn.querySelector && ctn.querySelector('.hp-export');
        row.appendChild(ctn);
        const labels = (m.series||[]).map(p=> p.t_utc || p.t || '');
        const vals = (m.series||[]).map(p=> p.v == null ? null : parseFloat(p.v));
        try{ createChart(canvas, m.metric, labels, vals, (m.series||[]), el._hp_current_agg || 'daily'); }catch(e){ console.warn('createChart failed', e); }
        if(btn) btn.addEventListener('click', ()=> _downloadCSV(m.metric, m.series));
      });
      body.appendChild(row);
    }catch(e){ console.warn('renderCharts error', e); }
  }

  async function fetchSeries(person, agg){
    try{
      console.debug('labs_critical_v2: fetchSeries', person, agg);
      const q = new URL('/labs/' + encodeURIComponent(person) + '/critical-series', location.origin);
      if(agg) q.searchParams.set('agg', agg);
      q.searchParams.set('metrics', 'hr,spo2');
      const res = await fetch(q.toString(), {cache:'no-store'});
      if(!res.ok) throw res.status;
      return res.json();
    }catch(e){ throw e; }
  }

  async function loadWithAgg(el, aggPref, preferPreview=false){
    const person = el.getAttribute('data-person-id') || '';
    if(!person){ if($('.hp-labs-body', el)) $('.hp-labs-body', el).innerHTML = '<div class="hp-empty">No person</div>'; return; }
    if(preferPreview){
      const pd = await fetchPreview(person);
      if(pd){ renderCharts(el, pd); return; }
    }
    try{
      const data = await fetchSeries(person, aggPref);
      el._hp_current_agg = aggPref || 'daily';
      if(!data || data.length === 0){
        const pd = await fetchPreview(person);
        if(pd){ renderCharts(el, pd); return; }
        if($('.hp-labs-body', el)) $('.hp-labs-body', el).innerHTML = '<div class="hp-empty">No lab series available</div>';
        return;
      }
      renderCharts(el, data);
    }catch(e){
      console.warn('labs_critical_v2: fetchSeries failed', e);
      const pd = await fetchPreview(person);
      if(pd){ el._hp_current_agg = 'preview'; renderCharts(el, pd); return; }
      if($('.hp-labs-body', el)) $('.hp-labs-body', el).innerHTML = '<div class="hp-error">Error loading labs</div>';
    }
  }

  function initToolbar(el){
    try{
      const toolbar = el.querySelector('.hp-labs-toolbar'); if(!toolbar) return; toolbar.innerHTML = '';
      const status = document.createElement('span'); status.style.marginRight = '12px'; status.setAttribute('aria-live','polite');
      const scopeSel = document.createElement('select'); scopeSel.innerHTML = '<option value=\"person\">This person</option><option value=\"global\">Global</option>'; scopeSel.style.marginRight='8px';
      const toggleBtn = document.createElement('button'); toggleBtn.className='hp-export'; toggleBtn.type='button';
      const aggSel = document.createElement('select'); aggSel.innerHTML = '<option value=\"daily\">Daily</option><option value=\"hourly\">Hourly</option>'; aggSel.style.marginRight='8px'; aggSel.setAttribute('aria-label','Aggregation');

      const person = el.getAttribute('data-person-id') || 'global';
      const globalKey = 'labs_mode_global';
      const personKey = `labs_mode_${person}`;
      const scopeKey = 'labs_mode_scope';
      const savedScope = localStorage.getItem(scopeKey) || 'person';
      scopeSel.value = savedScope === 'global' ? 'global' : 'person';
      const aggKey = `hp:labs:agg:${person}`;
      const defaultAgg = el.getAttribute('data-agg-default') || 'daily';
      const savedAgg = localStorage.getItem(aggKey) || defaultAgg;
      aggSel.value = savedAgg;

      function getActiveKey(){ return (scopeSel.value === 'global') ? globalKey : personKey; }
      function getMode(){ return localStorage.getItem(getActiveKey()) || 'live'; }
      function applyMode(mode){
        localStorage.setItem(getActiveKey(), mode); localStorage.setItem(scopeKey, scopeSel.value);
        if(mode === 'live'){ status.textContent = 'Mode: Live (shows real data)'; toggleBtn.textContent = 'Switch to Preview'; toggleBtn.setAttribute('aria-pressed','false'); loadWithAgg(el, aggSel.value, false); }
        else { status.textContent = 'Mode: Preview (shows sample data)'; toggleBtn.textContent = 'Switch to Live'; toggleBtn.setAttribute('aria-pressed','true'); fetchPreview(person).then(pd => { if(pd) renderCharts(el, pd); }); }
      }

      scopeSel.addEventListener('change', ()=>{ localStorage.setItem(scopeKey, scopeSel.value); const m = getMode(); applyMode(m); });
      toggleBtn.addEventListener('click', ()=>{ const cur = getMode(); applyMode(cur==='live'?'preview':'live'); });
      aggSel.addEventListener('change', ()=>{ localStorage.setItem(aggKey, aggSel.value); const mode = getMode(); if(mode==='live'){ loadWithAgg(el, aggSel.value, false); } else { fetchPreview(person).then(pd=>{ if(pd) renderCharts(el, pd); }); } });

      const bandsKey = 'hp_bands_enabled';
      const bandsEnabled = storageGet(bandsKey,'true') === 'true';
      const bandsToggle = document.createElement('button'); bandsToggle.type='button'; bandsToggle.className='hp-bands-toggle';
      bandsToggle.textContent = 'Show reference bands'; bandsToggle.setAttribute('aria-pressed', bandsEnabled ? 'true' : 'false');
      bandsToggle.style.marginRight='8px'; bandsToggle.style.cursor='pointer';

      const exportAll = document.createElement('button'); exportAll.type='button'; exportAll.className='hp-export-all';
      exportAll.textContent = 'Export CSV (All Visible)'; exportAll.style.marginRight='8px';

      bandsToggle.addEventListener('click', ()=>{
        const cur = bandsToggle.getAttribute('aria-pressed') === 'true'; const next = !cur; bandsToggle.setAttribute('aria-pressed', next ? 'true' : 'false');
        storageSet(bandsKey, next);
        try{ CHARTS.forEach(m => { if(m && m.chart){ m.chart.config._refBands = next ? REF_BANDS[m.metricKey || canonicalMetric(m.metric)] : null; try{ m.chart.update(); }catch(_){}}}); }catch(e){}
      });

      exportAll.addEventListener('click', ()=>{
        try{
          const personId = el.getAttribute('data-person-id') || 'current';
          const agg = el._hp_current_agg || aggSel.value || 'daily';
          const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
          const header = ['# timezone: '+tz];
          const rows = [['metric','agg','t_utc','t_local','value']];
          CHARTS.forEach(m => {
            const mk = m.metricKey || canonicalMetric(m.metric);
            const visible = storageGet('hp_series_visible.'+mk, 'true') === 'true';
            if(visible && Array.isArray(m.rawSeries)){
              const toExport = (agg === 'hourly') ? downsample(m.rawSeries, 2000) : m.rawSeries.slice();
              toExport.forEach(p => rows.push([m.metric, m.agg||agg, p.t_utc||p.t||'', p.t_local||'', (p.v==null?'':String(p.v))]));
            }
          });
          const csv = header.join('\n') + '\n' + rows.map(r => r.map(c => '"' + String(c).replace(/"/g,'""') + '"').join(',')).join('\n');
          const blob = new Blob([csv], {type:'text/csv'});
          const now = new Date(); const pad = n=> String(n).padStart(2,'0');
          const ts = now.getFullYear()+''+pad(now.getMonth()+1)+''+pad(now.getDate())+'-'+pad(now.getHours())+''+pad(now.getMinutes());
          const filename = 'labs_'+(personId||'current')+'_'+(agg||'')+'_'+ts+'.csv';
          const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = filename.replace(/[^a-z0-9_\\-\\.]/gi,'_'); document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
        }catch(e){ console.warn('exportAll failed', e); }
      });

      toolbar.appendChild(status); toolbar.appendChild(scopeSel); toolbar.appendChild(aggSel); toolbar.appendChild(bandsToggle); toolbar.appendChild(exportAll); toolbar.appendChild(toggleBtn);
      applyMode(getMode());
    }catch(e){ console.warn('initToolbar error', e); }
  }

  function boot(){
    document.querySelectorAll(SEL).forEach(el => initToolbar(el));
  }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();

})();
