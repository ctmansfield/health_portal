// labs_critical_v2.js - updated: reference bands, accessible legend, export-all CSV
(function(){
  'use strict';
  const sel = '.hp-labs-critical';
  const $ = (q, el=document) => el.querySelector(q);

  function escapeHtml(s){ return String(s).replace(/[&<>"']/g, ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[ch]); }

  function hashSeries(data){ try{ return JSON.stringify(data).length; }catch(e){ return String(Date.now()); } }

  // Reference bands (canonical keys)
  const REF_BANDS = { hr:[{label:'Normal',min:60,max:100}], spo2:[{label:'Healthy',min:94,max:100}] };

  function canonicalMetric(metric){ try{ return String(metric||'').toLowerCase().replace(/[^a-z0-9]/g,''); }catch(e){ return String(metric||''); } }
  function downsample(points, maxPoints=2000){ if(!Array.isArray(points)) return points; const len=points.length; if(len<=maxPoints) return points.slice(); const stride=Math.ceil(len/maxPoints); return points.filter((_,i)=> (i%stride)===0); }
  function storageGet(k,d){ try{ const v=localStorage.getItem(k); return v==null? d: v; }catch(e){ return d; } }
  function storageSet(k,v){ try{ localStorage.setItem(k,String(v)); }catch(e){}
  }

  // ... rest of file remains unchanged ...

  'use strict';
  const sel = '.hp-labs-critical';
  const $ = (q, el=document) => el.querySelector(q);

  function escapeHtml(s){ return String(s).replace(/[&<>"']/g, ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[ch]); }

  // Small util to shallow hash data (lightweight)
  function hashSeries(data){
    try{ return JSON.stringify(data).length; }catch(e){ return String(Date.now()); }
  }

  // Reference bands per metric
  const REF_BANDS = {
    hr:   [{label: 'Normal',  min: 60,  max: 100}],
    spo2: [{label: 'Healthy', min: 94,  max: 100}],
    // extend for other metrics as needed
  };

  // downsample helper for dense hourly series
  function downsample(points, maxPoints=2000){
    if(!Array.isArray(points)) return points;
    const len = points.length;
    if(len <= maxPoints) return points.slice();
    const stride = Math.ceil(len / maxPoints);
    return points.filter((_,i) => (i % stride) === 0);
  }

  function storageGet(key, def){
    try{ const v = localStorage.getItem(key); return v == null ? def : v; }catch(e){ return def; }
  }
  function storageSet(key, val){
    try{ localStorage.setItem(key, String(val)); }catch(e){}
  }

  // canonicalize metric names for lookups and storage
  function canonicalMetric(metric){
    try{ return String(metric||'').toLowerCase().replace(/[^a-z0-9]/g,''); }catch(e){ return String(metric||''); }
  }

  function makeChartContainer(metric){
    const wrapper = document.createElement('div');
    wrapper.className = 'hp-labs-chart';
    wrapper.innerHTML = '\
      <figure>\
        <h4>' + escapeHtml(metric) + '</h4>\
        <canvas aria-label="' + escapeHtml(metric) + ' chart" role="img"></canvas>\
        <figcaption class="hp-caption">Series for ' + escapeHtml(metric) + '. Use the export button to download CSV. Double-click to reset zoom. Shift+wheel to pan.</figcaption>\
        <div style="margin-top:8px;display:flex;gap:8px;align-items:center">\
          <div class="hp-legend" role="list" aria-label="Series legend"></div>\
          <div style="margin-left:auto"><button class="hp-export" type="button">Export CSV</button></div>\
        </div>\
      </figure>';
    return wrapper;
  }

  function renderLoading(el){
    const body = $('.hp-labs-body', el);
    body.innerHTML='';
    const row=document.createElement('div'); row.className='hp-labs-row';
    for(let i=0;i<2;i++){const sk=document.createElement('div'); sk.className='hp-labs-skel'; sk.style.width='48%'; row.appendChild(sk);}
    body.appendChild(row);
  }
  function renderEmpty(el){ $('.hp-labs-body', el).innerHTML = '<div class="hp-empty">No lab series available</div>'; }
  function renderError(el, status){ $('.hp-labs-body', el).innerHTML = '<div class="hp-error">Error loading labs (' + (status||'network') + ')</div>'; }

  function _downloadCSV(metric, series){
    const rows = [['t_utc','t_local','value']];
    (series || []).forEach(p=> rows.push([p.t_utc||p.t||'', p.t_local||'', p.v==null? '': String(p.v)]));
    const csvRows = rows.map(r=> r.map(c => '"' + String(c).replace(/"/g,'""') + '"').join(',')).join('\n');
    const blob = new Blob([csvRows], {type:'text/csv'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url;
    a.download = metric.replace(/[^a-z0-9]/gi,'_') + '_series.csv';
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  }

  // module state
  const CHARTS = []; // { canvas, chart, overlay, metric, hash, handlers, rawSeries, agg }

  // Preview fetch throttle/cache
  const PREVIEW = { key:null, data:null, ts:0, inflight:null, ttl: 30_000 };

  async function fetchPreview(person){
    const key = String(person||'');
    const now = Date.now();
    if(PREVIEW.key === key && PREVIEW.data && (now - PREVIEW.ts) < PREVIEW.ttl){
      console.debug('labs_critical_v2: preview cache hit');
      return PREVIEW.data;
    }
    if(PREVIEW.inflight){
      try{ console.debug('labs_critical_v2: awaiting inflight preview'); return await PREVIEW.inflight; }catch(e){ return null; }
    }
    PREVIEW.inflight = (async ()=>{
      try{
        console.debug('labs_critical_v2: fetching preview for', 'person=current');
        const res = await fetch('/ui/preview/labs/' + encodeURIComponent(key), {cache:'no-store'});
        if(!res.ok) return null;
        const j = await res.json();
        PREVIEW.key = key; PREVIEW.data = j; PREVIEW.ts = Date.now();
        return j;
      }catch(e){
        console.warn('labs_critical_v2: preview fetch error', e);
        return null;
      } finally {
        PREVIEW.inflight = null;
      }
    })();
    try{ return await PREVIEW.inflight; }catch(e){ return null; }
  }

  // Create/destroy charts safely
  function createChart(canvas, metric, labels, vals, rawSeries, agg){
    // Avoid double-creating for identical data
    const dataHash = hashSeries(labels) + ':' + hashSeries(vals) + ':' + (hashSeries(rawSeries)||'');
    if(canvas._hp_hash === dataHash && canvas._hp_chart){
      // already up-to-date
      console.debug('labs_critical_v2: chart up-to-date for', metric);
      return canvas._hp_meta;
    }

    // destroy previous
    try{ if(canvas._hp_chart && typeof canvas._hp_chart.destroy === 'function') canvas._hp_chart.destroy(); }catch(e){ console.warn('labs_critical_v2: destroy error', e); }

    // FIX: stable CSS height/backing store
    const parent = canvas.parentElement || canvas;
    const cssW = parent.clientWidth || 600;
    const cssH = 160;
    const dpr = window.devicePixelRatio || 1;
    canvas.style.width = cssW + 'px';
    canvas.style.height = cssH + 'px';
    canvas.width = Math.max(1, Math.floor(cssW * dpr));
    canvas.height = Math.max(1, Math.floor(cssH * dpr));
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr,0,0,dpr,0,0);

    // plugin to render reference bands under datasets
    const refBandsPlugin = {
      id: 'refBands',
      beforeDatasetsDraw(chart){
        try{
          const bandCfg = chart.config._refBands; if(!bandCfg || !Array.isArray(bandCfg)) return;
          const yScale = chart.scales.y;
          const ctx = chart.ctx; const chartArea = chart.chartArea;
          bandCfg.forEach((b, idx)=>{
            if(b.min == null || b.max == null) return;
            const y1 = yScale.getPixelForValue(b.max);
            const y2 = yScale.getPixelForValue(b.min);
            ctx.save();
            ctx.fillStyle = 'rgba(34,197,94,0.08)';
            ctx.fillRect(chartArea.left, y1, chartArea.right - chartArea.left, Math.max(1, y2 - y1));
            ctx.restore();
          });
        }catch(e){ /* silence */ }
      }
    };

    const cfg = {
      type: 'line',
      data: { labels: labels.slice(), datasets: [{ label: metric, data: vals.slice(), borderColor:'#2563eb', tension:0.2, pointRadius:1, fill:false }] },
      options: { responsive: false, maintainAspectRatio: false, plugins:{legend:{display:false}}, interaction:{intersect:false}, scales:{ x:{display:true}, y:{beginAtZero:false} } },
      plugins: [refBandsPlugin]
    };

    const metricKey = canonicalMetric(metric);
    // read stored preference (default true) and UI toggle if present
    const storedBands = storageGet('hp_bands_enabled', 'true') === 'true';
    const bandsToggleEl = document.querySelector('.hp-bands-toggle');
    const uiToggle = bandsToggleEl && typeof bandsToggleEl.getAttribute === 'function' ? bandsToggleEl.getAttribute('aria-pressed') === 'true' : false;
    const bandsEnabled = uiToggle || storedBands;
    if(bandsEnabled && REF_BANDS[metricKey]) cfg._refBands = REF_BANDS[metricKey];

    const chart = new Chart(ctx, cfg);
    canvas._hp_chart = chart;
    canvas._hp_hash = dataHash;

    const meta = { canvas, chart, metric, metricKey: canonicalMetric(metric), hash: dataHash, labels: labels.slice(), vals: vals.slice(), rawSeries: rawSeries ? rawSeries.slice() : [], agg: agg || 'daily', overlay:null, handlers:{} };
    canvas._hp_meta = meta;

    attachInteractions(meta);

    // create accessible legend control
    try{
      const parentEl = canvas.parentElement;
      const legendRoot = parentEl.querySelector('.hp-legend');
      if(legendRoot){
        legendRoot.innerHTML = '';
        const item = document.createElement('div'); item.setAttribute('role','listitem');
        const btn = document.createElement('button'); btn.type='button'; btn.className='hp-legend-toggle';
        btn.setAttribute('data-series', metricKey);
        const stored = storageGet('hp_series_visible.'+metricKey, 'true') === 'true';
        btn.setAttribute('aria-pressed', stored ? 'true' : 'false');
        btn.textContent = metric;
        btn.style.padding = '4px 8px';
        btn.style.borderRadius = '6px';
        btn.style.border = '1px solid #e6eef8';
        btn.style.background = stored ? '#eefbf3' : '#fff';
        btn.style.cursor = 'pointer';
        btn.addEventListener('click', ()=>{
          const cur = btn.getAttribute('aria-pressed') === 'true';
          const next = !cur; btn.setAttribute('aria-pressed', next ? 'true' : 'false');
          storageSet('hp_series_visible.'+metricKey, next);
          try{ meta.chart.data.datasets[0].hidden = !next; meta.chart.update(); }catch(e){}
          btn.style.background = next ? '#eefbf3' : '#fff';
        });
        btn.addEventListener('keydown', (ev)=>{ if(ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); btn.click(); } });
        item.appendChild(btn);
        legendRoot.appendChild(item);
        // apply initial visibility
        try{ meta.chart.data.datasets[0].hidden = !(storageGet('hp_series_visible.'+metricKey, 'true') === 'true'); meta.chart.update(); }catch(e){}
      }
    }catch(e){ /* ignore */ }

    CHARTS.push(meta);
    console.debug('labs_critical_v2: created chart for', metric);
    return meta;
  }

  function destroyMeta(meta){
    if(!meta) return;
    try{ if(meta.chart && typeof meta.chart.destroy === 'function') meta.chart.destroy(); }catch(e){}
    try{ if(meta.overlay && meta.overlay.parentElement) meta.overlay.parentElement.removeChild(meta.overlay); }catch(e){}
    try{
      const c = meta.canvas;
      if(c){
        if(meta.handlers.onPointerDown) c.removeEventListener('pointerdown', meta.handlers.onPointerDown);
        if(meta.handlers.onPointerMove) c.removeEventListener('pointermove', meta.handlers.onPointerMove);
        if(meta.handlers.onPointerUp) c.removeEventListener('pointerup', meta.handlers.onPointerUp);
        if(meta.handlers.onPointerCancel) c.removeEventListener('pointercancel', meta.handlers.onPointerCancel);
        if(meta.handlers.onDblClick) c.removeEventListener('dblclick', meta.handlers.onDblClick);
        if(meta.handlers.onWheel) c.removeEventListener('wheel', meta.handlers.onWheel);
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

  function attachInteractions(meta){
    const canvas = meta.canvas;
    // overlay inside the canvas parent that will not affect layout
    const overlay = document.createElement('div');
    overlay.style.position = 'absolute';
    overlay.style.pointerEvents = 'none';
    overlay.style.background = 'rgba(37,99,235,0.12)';
    overlay.style.border = '1px dashed rgba(37,99,235,0.4)';
    overlay.style.display = 'none';
    overlay.style.zIndex = 5;
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.height = '100%';
    overlay.style.width = '0px';
    overlay.style.boxSizing = 'border-box';

    const parent = canvas.parentElement;
    parent.style.position = parent.style.position || 'relative';
    parent.appendChild(overlay);
    meta.overlay = overlay;

    let dragging = false, dragStartX = 0, dragEndX = 0;

    function getTimeAtX(x){
      const rect = canvas.getBoundingClientRect();
      const rel = Math.max(0, Math.min(1, (x - rect.left) / rect.width));
      const idx = Math.floor(rel * (meta.labels.length - 1));
      return meta.labels[Math.max(0, Math.min(meta.labels.length - 1, idx))];
    }

    // handlers
    meta.handlers.onPointerDown = function(ev){
      if(ev.button !== 0) return;
      dragging = true;
      dragStartX = ev.clientX; dragEndX = dragStartX;
      overlay.style.display = 'block';
      const rect = canvas.getBoundingClientRect();
      overlay.style.left = (dragStartX - rect.left) + 'px';
      overlay.style.width = '0px';
      try{ canvas.setPointerCapture(ev.pointerId); }catch(e){}
    };
    meta.handlers.onPointerMove = function(ev){
      if(!dragging) return;
      dragEndX = ev.clientX;
      const rect = canvas.getBoundingClientRect();
      const left = Math.min(dragStartX, dragEndX), right = Math.max(dragStartX, dragEndX);
      overlay.style.left = Math.max(0, left - rect.left) + 'px';
      overlay.style.width = Math.max(2, right - left) + 'px';
      overlay.style.top = '0px';
      overlay.style.height = rect.height + 'px';
    };
    meta.handlers.onPointerUp = function(ev){
      if(!dragging) return;
      dragging = false;
      overlay.style.display = 'none';
      try{ canvas.releasePointerCapture(ev.pointerId); }catch(e){}
      const startTime = getTimeAtX(dragStartX), endTime = getTimeAtX(dragEndX);
      if(startTime && endTime && startTime !== endTime){
        const s = startTime < endTime ? startTime : endTime;
        const e = startTime < endTime ? endTime : startTime;
        applyViewWindowToAll(s, e);
      }
    };
    meta.handlers.onPointerCancel = function(){ if(dragging){ dragging=false; overlay.style.display='none'; } };
    meta.handlers.onDblClick = function(){ resetAllViews(); };
    meta.handlers.onWheel = function(ev){
      if(!ev.shiftKey) return;
      ev.preventDefault();
      const labels = meta.labels;
      const len = labels.length; if(len <= 1) return;
      const curStart = meta.viewStart == null ? 0 : meta.viewStart;
      const curEnd = meta.viewEnd == null ? len-1 : meta.viewEnd;
      const win = curEnd - curStart + 1;
      const step = Math.max(1, Math.floor(win * 0.15));
      const delta = ev.deltaY > 0 ? 1 : -1;
      let newStart = curStart + delta * step;
      let newEnd = curEnd + delta * step;
      if(newStart < 0){ newStart = 0; newEnd = Math.min(len-1, newStart + win -1); }
      if(newEnd > len-1){ newEnd = len-1; newStart = Math.max(0, newEnd - win +1); }
      const startTime = labels[newStart], endTime = labels[newEnd];
      applyViewWindowToAll(startTime, endTime);
    };

    // attach
    canvas.addEventListener('pointerdown', meta.handlers.onPointerDown);
    canvas.addEventListener('pointermove', meta.handlers.onPointerMove);
    canvas.addEventListener('pointerup', meta.handlers.onPointerUp);
    canvas.addEventListener('pointercancel', meta.handlers.onPointerCancel);
    canvas.addEventListener('dblclick', meta.handlers.onDblClick);
    canvas.addEventListener('wheel', meta.handlers.onWheel, {passive:false});
    console.debug('labs_critical_v2: interactions attached for', meta.metric);
  }

  function renderCharts(el, data){
    // throttle frequent re-renders
    if(el._lastRender && (Date.now() - el._lastRender) < 300){
      console.debug('labs_critical_v2: skipping rapid re-render');
      return;
    }
    el._lastRender = Date.now();

    // cleanup
    while(CHARTS.length){
      const meta = CHARTS.pop();
      try{ destroyMeta(meta); }catch(e){}
    }

    const body = $('.hp-labs-body', el);
    body.innerHTML = '';
    const row = document.createElement('div'); row.className = 'hp-labs-row';

    data.forEach(m=>{
      const ctn = makeChartContainer(m.metric);
      const canvas = ctn.querySelector('canvas');
      const btn = ctn.querySelector('.hp-export');
      row.appendChild(ctn);

      const labels = (m.series || []).map(p => p.t_utc || p.t || '');
      const vals = (m.series || []).map(p => p.v == null ? null : parseFloat(p.v));

      try{ createChart(canvas, m.metric, labels, vals, (m.series||[]), el._hp_current_agg || 'daily'); }catch(e){ console.warn('labs_critical_v2: createChart failed', e); }
      if(btn){ btn.addEventListener('click', ()=>_downloadCSV(m.metric, m.series)); }
    });

    body.appendChild(row);
  }

  async function fetchSeries(person, agg){
    console.debug('labs_critical_v2: fetchSeries', 'person=current', agg);
    const q = new URL('/labs/' + encodeURIComponent(person) + '/critical-series', location.origin);
    if(agg) q.searchParams.set('agg', agg);
    q.searchParams.set('metrics', 'hr,spo2');
    const res = await fetch(q.toString(), {cache:'no-store'});
    if(!res.ok) throw res.status;
    return res.json();
  }

  async function loadWithAgg(el, aggPref, preferPreview=false){
    const person = el.getAttribute('data-person-id') || '';
    if(!person){ renderEmpty(el); return; }
    renderLoading(el);

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
        renderEmpty(el); return;
      }
      renderCharts(el, data);
    }catch(e){
      console.warn('labs_critical_v2: fetchSeries failed', e);
      const pd = await fetchPreview(person);
      if(pd){ el._hp_current_agg = 'preview'; renderCharts(el, pd); return; }
      renderError(el, e);
    }
  }

  function initToolbar(el){
    const toolbar = el.querySelector('.hp-labs-toolbar'); if(!toolbar) return; toolbar.innerHTML='';
    const status = document.createElement('span'); status.style.marginRight='12px'; status.setAttribute('aria-live','polite');
    const scopeSel = document.createElement('select'); scopeSel.innerHTML = '<option value="person">This person</option><option value="global">Global</option>'; scopeSel.style.marginRight='8px';
    const toggleBtn = document.createElement('button'); toggleBtn.className='hp-export'; toggleBtn.type='button';

    const aggSel = document.createElement('select'); aggSel.innerHTML = '<option value="daily">Daily</option><option value="hourly">Hourly</option>'; aggSel.style.marginRight='8px'; aggSel.setAttribute('aria-label','Aggregation');

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
      localStorage.setItem(getActiveKey(), mode);
      localStorage.setItem(scopeKey, scopeSel.value);
      if(mode === 'live'){
        status.textContent = 'Mode: Live (shows real data)';
        toggleBtn.textContent = 'Switch to Preview';
        toggleBtn.setAttribute('aria-pressed','false');
        loadWithAgg(el, aggSel.value, false);
      } else {
        status.textContent = 'Mode: Preview (shows sample data)';
        toggleBtn.textContent = 'Switch to Live';
        toggleBtn.setAttribute('aria-pressed','true');
        fetchPreview(person).then(pd => { if(pd) renderCharts(el, pd); });
      }
    }

    // reference bands toggle and export-all
    const bandsKey = 'hp_bands_enabled';
    const bandsEnabled = storageGet(bandsKey, 'true') === 'true';
    const bandsToggle = document.createElement('button'); bandsToggle.type='button'; bandsToggle.className='hp-bands-toggle';
    bandsToggle.textContent = 'Show reference bands'; bandsToggle.setAttribute('aria-pressed', bandsEnabled ? 'true' : 'false');
    bandsToggle.style.marginRight='8px';
    bandsToggle.style.cursor = 'pointer';

    const exportAll = document.createElement('button'); exportAll.type='button'; exportAll.className='hp-export-all'; exportAll.textContent='Export CSV (All Visible)'; exportAll.style.marginRight='8px';

    scopeSel.addEventListener('change', ()=>{
      localStorage.setItem(scopeKey, scopeSel.value);
      const m = getMode(); applyMode(m);
    });

    toggleBtn.addEventListener('click', ()=>{
      const cur = getMode(); applyMode(cur === 'live' ? 'preview' : 'live');
    });

    aggSel.addEventListener('change', ()=>{
      localStorage.setItem(aggKey, aggSel.value);
      const mode = getMode();
      if(mode === 'live'){ loadWithAgg(el, aggSel.value, false); } else { fetchPreview(person).then(pd=>{ if(pd) renderCharts(el, pd); }); }
    });

    bandsToggle.addEventListener('click', ()=>{
      const cur = bandsToggle.getAttribute('aria-pressed') === 'true';
      const next = !cur;
      bandsToggle.setAttribute('aria-pressed', next ? 'true' : 'false');
      storageSet(bandsKey, next);
      try{
        CHARTS.forEach(m=>{
          if(m.chart){
            m.chart.config._refBands = next ? REF_BANDS[m.metricKey || canonicalMetric(m.metric)] : null;
            m.chart.update();
          }
        });
      }catch(e){}
    });

    exportAll.addEventListener('click', ()=>{
      try{
        const personId = el.getAttribute('data-person-id') || 'current';
        const agg = el._hp_current_agg || aggSel.value || 'daily';
        const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
        const header = ['# timezone: '+tz];
        const rows = [['metric','agg','t_utc','t_local','value']];
        CHARTS.forEach(m=>{
          const visible = storageGet('hp_series_visible.' + (m.metricKey || canonicalMetric(m.metric)), 'true') === 'true';
          if(visible && Array.isArray(m.rawSeries)){
            const toExport = (agg === 'hourly') ? downsample(m.rawSeries, 2000) : m.rawSeries.slice();
            toExport.forEach(p=> rows.push([m.metric, m.agg||agg, p.t_utc||p.t||'', p.t_local||'', (p.v==null?'':String(p.v))]));
          }
        });
        const csv = header.join('\n') + '\n' + rows.map(r=> r.map(c => '"' + String(c).replace(/"/g,'""') + '"').join(',')).join('\n');
        const blob = new Blob([csv], {type:'text/csv'});
        const now = new Date();
        const pad = n=> String(n).padStart(2,'0');
        const ts = now.getFullYear()+''+pad(now.getMonth()+1)+''+pad(now.getDate())+'-'+pad(now.getHours())+''+pad(now.getMinutes());
        const filename = 'labs_'+ (personId || 'current') + '_' + (agg||'') + '_' + ts + '.csv';
        const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = filename.replace(/[^a-z0-9_\-\.]/gi,'_'); document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
      }catch(e){ console.warn('labs_critical_v2: export failed', e); }
    });

    toolbar.appendChild(status);
    toolbar.appendChild(scopeSel);
    toolbar.appendChild(aggSel);
    toolbar.appendChild(bandsToggle);
    toolbar.appendChild(exportAll);
    toolbar.appendChild(toggleBtn);

    applyMode(getMode());
  }

  function boot(){
    document.querySelectorAll(sel).forEach(el=> initToolbar(el));
  }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
