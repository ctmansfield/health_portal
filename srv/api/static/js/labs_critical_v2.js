// labs_critical_v2.js - final defensive version (throttled preview, stable sizing, destroy-on-replace)
(function(){
  'use strict';
  const sel = '.hp-labs-critical';
  const $ = (q, el=document) => el.querySelector(q);

  function escapeHtml(s){ return String(s).replace(/[&<>"']/g, ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[ch]); }

  // Small util to shallow hash data (lightweight)
  function hashSeries(data){
    try{ return JSON.stringify(data).length; }catch(e){ return String(Date.now()); }
  }

  function makeChartContainer(metric){
    const wrapper = document.createElement('div');
    wrapper.className = 'hp-labs-chart';
    wrapper.innerHTML = '\
      <figure>\
        <h4>' + escapeHtml(metric) + '</h4>\
        <canvas aria-label="' + escapeHtml(metric) + ' chart" role="img"></canvas>\
        <figcaption class="hp-caption">Series for ' + escapeHtml(metric) + '. Use the export button to download CSV. Double-click to reset zoom. Shift+wheel to pan.</figcaption>\
        <div style="margin-top:8px"><button class="hp-export" type="button">Export CSV</button></div>\
      </figure>';
    return wrapper;
  }

  function renderLoading(el){ const body = $('.hp-labs-body', el); body.innerHTML=''; const row=document.createElement('div'); row.className='hp-labs-row'; for(let i=0;i<2;i++){const sk=document.createElement('div'); sk.className='hp-labs-skel'; sk.style.width='48%'; row.appendChild(sk);} body.appendChild(row); }
  function renderEmpty(el){ $('.hp-labs-body', el).innerHTML = '<div class="hp-empty">No lab series available</div>'; }
  function renderError(el, status){ $('.hp-labs-body', el).innerHTML = '<div class="hp-error">Error loading labs (' + (status||'network') + ')</div>'; }

  function _downloadCSV(metric, series){
    const rows = [['t_utc','t_local','value']];
    series.forEach(p=> rows.push([p.t_utc||p.t||'', p.t_local||'', p.v==null? '': String(p.v)]));
    const csvRows = rows.map(r=> r.map(c => '"' + String(c).replace(/"/g,'""') + '"').join(',')).join('\n');
    const blob = new Blob([csvRows], {type:'text/csv'});
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = metric.replace(/[^a-z0-9]/gi,'_') + '_series.csv'; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  }

  // module state
  const CHARTS = []; // { canvas, chart, overlay, metric, hash, handlers }

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
        console.debug('labs_critical_v2: fetching preview for', key);
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
  function createChart(canvas, metric, labels, vals){
    // Avoid double-creating for identical data
    const dataHash = hashSeries(labels) + ':' + hashSeries(vals);
    if(canvas._hp_hash === dataHash && canvas._hp_chart){
      // already up-to-date
      console.debug('labs_critical_v2: chart up-to-date for', metric);
      return canvas._hp_meta;
    }

    // destroy previous
    try{ if(canvas._hp_chart && typeof canvas._hp_chart.destroy === 'function') canvas._hp_chart.destroy(); }catch(e){ console.warn('labs_critical_v2: destroy error', e); }

    // FIX: set a stable CSS height once and set backing store to devicePixelRatio-sized pixels.
    // This avoids a resize observer loop when Chart.js tries to be responsive repeatedly.
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

    const cfg = {
      type: 'line',
      data: { labels: labels.slice(), datasets: [{ label: metric, data: vals.slice(), borderColor:'#2563eb', tension:0.2, pointRadius:1, fill:false }] },
      options: { responsive: false, maintainAspectRatio: false, plugins:{legend:{display:false}}, interaction:{intersect:false}, scales:{ x:{display:true}, y:{beginAtZero:false} } }
    };

    const chart = new Chart(ctx, cfg);
    canvas._hp_chart = chart;
    canvas._hp_hash = dataHash;

    const meta = { canvas, chart, metric, hash: dataHash, labels: labels.slice(), vals: vals.slice(), overlay:null, handlers:{} };
    canvas._hp_meta = meta;

    attachInteractions(meta);

    CHARTS.push(meta);
    console.debug('labs_critical_v2: created chart for', metric);
    return meta;
  }

  function destroyMeta(meta){
    if(!meta) return;
    try{ if(meta.chart && typeof meta.chart.destroy === 'function') meta.chart.destroy(); }catch(e){}
    // remove overlay if present
    try{ if(meta.overlay && meta.overlay.parentElement) meta.overlay.parentElement.removeChild(meta.overlay); }catch(e){}
    // remove any attached handlers
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
    // create an overlay absolutely positioned inside the canvas parent that will not affect layout
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
    // prevent very-frequent re-renders: check last render per element
    if(el._lastRender && (Date.now() - el._lastRender) < 300){
      console.debug('labs_critical_v2: skipping rapid re-render');
      return;
    }
    el._lastRender = Date.now();

    // cleanup previous charts and listeners
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

      try{ createChart(canvas, m.metric, labels, vals); }catch(e){ console.warn('labs_critical_v2: createChart failed', e); }
      if(btn){ btn.addEventListener('click', ()=>_downloadCSV(m.metric, m.series)); }
    });

    body.appendChild(row);
  }

  async function fetchSeries(person, agg){
    console.debug('labs_critical_v2: fetchSeries', person, agg);
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
      if(!data || data.length === 0){
        const pd = await fetchPreview(person);
        if(pd){ renderCharts(el, pd); return; }
        renderEmpty(el); return;
      }
      renderCharts(el, data);
    }catch(e){
      console.warn('labs_critical_v2: fetchSeries failed', e);
      const pd = await fetchPreview(person);
      if(pd){ renderCharts(el, pd); return; }
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

    toolbar.appendChild(status); toolbar.appendChild(scopeSel); toolbar.appendChild(aggSel); toolbar.appendChild(toggleBtn);
    applyMode(getMode());
  }

  function boot(){
    document.querySelectorAll(sel).forEach(el=> initToolbar(el));
  }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();