// labs_critical_v2.js — robust boot: helpers + Chart.js check + containers
(function(){
  'use strict';

  const sel = '.hp-labs-critical';
  const $ = (q, el=document) => el.querySelector(q);

  const hasChart = typeof window.Chart !== 'undefined';

  function escapeHtml(s){ return String(s).replace(/[&<>"']/g, ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[ch]); }
  function canonicalMetric(metric){ try{ return String(metric||'').toLowerCase().replace(/[^a-z0-9]/g,''); }catch(e){ return String(metric||''); } }
  function hashSeries(data){ try{ return JSON.stringify(data).length; }catch(e){ return String(Date.now()); } }

  // minimal containers if template forgot them
  function ensureContainers(el){
    if (!$('.hp-labs-toolbar', el)) { const n = document.createElement('div'); n.className='hp-labs-toolbar'; el.prepend(n); }
    if (!$('.hp-labs-body', el))    { const n = document.createElement('div'); n.className='hp-labs-body'; el.appendChild(n); }
  }

  // lightweight rendering helpers (were missing)
  function renderLoading(el){
    const body = $('.hp-labs-body', el); if(!body) return;
    body.innerHTML = '<div class="hp-skeleton">Loading…</div>';
  }
  function renderEmpty(el){
    const body = $('.hp-labs-body', el); if(!body) return;
    body.innerHTML = '<p class="hp-muted">No data available for this window.</p>';
  }
  function renderError(el, e){
    const body = $('.hp-labs-body', el); if(!body) return;
    body.innerHTML = '<div class="hp-error">Error loading series: ' + escapeHtml(String(e)) + '</div>';
  }

  const REF_BANDS = { hr:[{label:'Normal',min:60,max:100}], spo2:[{label:'Healthy',min:94,max:100}] };
  function downsample(points, maxPoints=2000){ if(!Array.isArray(points)) return points; const len=points.length; if(len<=maxPoints) return points.slice(); const stride=Math.ceil(len/maxPoints); return points.filter((_,i)=>i%stride===0); }
  function storageGet(k, d){ try{ const v=localStorage.getItem(k); return v==null?d:v; }catch(e){ return d; } }
  function storageSet(k, v){ try{ localStorage.setItem(k, String(v)); }catch(e){} }

  function makeChartContainer(metric){
    const wrap = document.createElement('div');
    wrap.className = 'hp-labs-chart';
    wrap.innerHTML = `
      <figure>
        <h4>${escapeHtml(metric)}</h4>
        <div class="chart-wrap"><canvas aria-label="${escapeHtml(metric)} chart" role="img"></canvas></div>
        <figcaption class="hp-caption">Double-click to reset zoom. Shift+wheel to pan.</figcaption>
        <div class="hp-row">
          <div class="hp-legend" role="list" aria-label="Series legend"></div>
          <button class="hp-export" type="button">Export CSV</button>
        </div>
      </figure>`;
    return wrap;
  }

  function _downloadCSV(metric, series){
    const rows = [['t_utc','t_local','value']];
    (series||[]).forEach(p => rows.push([p.t_utc||p.t||'', p.t_local||'', p.v==null?'':String(p.v)]));
    const csv = rows.map(r=> r.map(c => '"' + String(c).replace(/"/g,'""') + '"').join(',')).join('\n');
    const blob = new Blob([csv], {type:'text/csv'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url;
    a.download = metric.replace(/[^a-z0-9]/gi,'_') + '_series.csv';
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  }

  const CHARTS = [];
  const PREVIEW = { key:null, data:null, ts:0, inflight:null, ttl:30000 };

  async function fetchPreview(person){
    const key = String(person||'');
    const now = Date.now();
    if(PREVIEW.key === key && PREVIEW.data && (now - PREVIEW.ts) < PREVIEW.ttl) return PREVIEW.data;
    if(PREVIEW.inflight){ try{ return await PREVIEW.inflight; }catch(e){ return null; } }
    PREVIEW.inflight = (async ()=>{
      try{
        const res = await fetch('/ui/preview/labs/' + encodeURIComponent(key), {cache:'no-store'});
        if(!res.ok) return null;
        const j = await res.json();
        PREVIEW.key = key; PREVIEW.data = j; PREVIEW.ts = Date.now();
        return j;
      }catch(e){ return null; } finally { PREVIEW.inflight = null; }
    })();
    try{ return await PREVIEW.inflight; }catch(e){ return null; }
  }

  function attachInteractions(meta){
    const canvas = meta.canvas, parent = canvas.parentElement;
    parent.style.position = parent.style.position || 'relative';
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:absolute;pointer-events:none;background:rgba(37,99,235,.12);border:1px dashed rgba(37,99,235,.4);display:none;top:0;left:0;height:100%;z-index:5;box-sizing:border-box;';
    parent.appendChild(overlay); meta.overlay = overlay;

    let dragging=false, startX=0, endX=0;
    function getTimeAtX(x){
      const rect = canvas.getBoundingClientRect();
      const rel = Math.max(0, Math.min(1, (x - rect.left)/rect.width));
      const idx = Math.floor(rel * (meta.labels.length - 1));
      return meta.labels[Math.max(0, Math.min(meta.labels.length -1, idx))];
    }

    meta.handlers = {};
    meta.handlers.onPointerDown = (ev)=>{ if(ev.button!==0) return; dragging=true; startX=ev.clientX; endX=startX; overlay.style.display='block'; const r=canvas.getBoundingClientRect(); overlay.style.left=(startX-r.left)+'px'; overlay.style.width='0px'; try{ canvas.setPointerCapture(ev.pointerId);}catch(e){} };
    meta.handlers.onPointerMove = (ev)=>{ if(!dragging) return; endX=ev.clientX; const r=canvas.getBoundingClientRect(); const L=Math.min(startX,endX), R=Math.max(startX,endX); overlay.style.left=Math.max(0, L-r.left)+'px'; overlay.style.width=Math.max(2, R-L)+'px'; overlay.style.height=r.height+'px'; };
    meta.handlers.onPointerUp   = (ev)=>{ if(!dragging) return; dragging=false; overlay.style.display='none'; try{ canvas.releasePointerCapture(ev.pointerId);}catch(e){} const t1=getTimeAtX(startX), t2=getTimeAtX(endX); if(t1&&t2&&t1!==t2){ const s=t1<t2?t1:t2, e=t1<t2?t2:t1; applyViewWindowToAll(s,e); } };
    meta.handlers.onDblClick    = ()=> resetAllViews();
    meta.handlers.onWheel       = (ev)=>{ if(!ev.shiftKey) return; ev.preventDefault(); const labels=meta.labels, len=labels.length; if(len<=1) return; const curStart=meta.viewStart??0; const curEnd=meta.viewEnd??(len-1); const win=curEnd-curStart+1; const step=Math.max(1, Math.floor(win*0.15)); const delta = ev.deltaY>0?1:-1; let s=curStart+delta*step, e=curEnd+delta*step; if(s<0){ s=0; e=Math.min(len-1, s+win-1);} if(e>len-1){ e=len-1; s=Math.max(0, e-win+1);} applyViewWindowToAll(labels[s], labels[e]); };

    canvas.addEventListener('pointerdown', meta.handlers.onPointerDown);
    canvas.addEventListener('pointermove', meta.handlers.onPointerMove);
    canvas.addEventListener('pointerup',   meta.handlers.onPointerUp);
    canvas.addEventListener('dblclick',    meta.handlers.onDblClick);
    canvas.addEventListener('wheel',       meta.handlers.onWheel, {passive:false});
  }

  function createChart(canvas, metric, labels, vals, rawSeries, agg){
    if(!hasChart){ console.error('Chart.js not loaded'); return null; }
    const dataHash = hashSeries(labels)+':'+hashSeries(vals)+':'+(hashSeries(rawSeries)||'');
    if(canvas._hp_hash === dataHash && canvas._hp_chart) return canvas._hp_meta;

    try{ if(canvas._hp_chart && typeof canvas._hp_chart.destroy==='function') canvas._hp_chart.destroy(); }catch(e){}
    const parent = canvas.parentElement || canvas;
    const cssW = parent.clientWidth || 600, cssH = parent.clientHeight || 240;
    const dpr = window.devicePixelRatio || 1;
    canvas.style.width = '100%'; canvas.style.height = '100%';
    canvas.width  = Math.max(1, Math.floor(cssW * dpr));
    canvas.height = Math.max(1, Math.floor(cssH * dpr));
    const ctx = canvas.getContext('2d'); ctx.setTransform(dpr,0,0,dpr,0,0);

    const refBandsPlugin = {
      id:'refBands',
      beforeDatasetsDraw(chart){
        const bands = chart.config._refBands; if(!bands) return;
        const y = chart.scales.y, a = chart.chartArea, c = chart.ctx;
        bands.forEach(b=>{ if(b.min==null||b.max==null) return; const y1=y.getPixelForValue(b.max), y2=y.getPixelForValue(b.min); c.save(); c.fillStyle='rgba(34,197,94,0.08)'; c.fillRect(a.left,y1,a.right-a.left, Math.max(1, y2-y1)); c.restore(); });
      }
    };

    const cfg = {
      type:'line',
      data:{ labels:labels.slice(), datasets:[{ label:metric, data:vals.slice(), borderColor:'#2563eb', tension:0.2, pointRadius:1, fill:false }] },
      options:{ responsive:false, maintainAspectRatio:false, plugins:{ legend:{display:false} }, interaction:{intersect:false}, scales:{x:{display:true}, y:{beginAtZero:false}} },
      plugins:[refBandsPlugin]
    };

    const metricKey = canonicalMetric(metric);
    const storedBands = storageGet('hp_bands_enabled','true')==='true';
    if(storedBands && REF_BANDS[metricKey]) cfg._refBands = REF_BANDS[metricKey];

    const chart = new Chart(ctx, cfg);
    canvas._hp_chart = chart; canvas._hp_hash = dataHash;

    const meta = { canvas, chart, metric, metricKey, hash:dataHash, labels:labels.slice(), vals:vals.slice(), rawSeries:rawSeries?rawSeries.slice():[], agg:agg||'daily', overlay:null, handlers:{}, origPointRadius:1 };
    canvas._hp_meta = meta;

    attachInteractions(meta);

    // simple legend with show/hide
    try{
      const legendRoot = (canvas.parentElement||document).querySelector('.hp-legend');
      if(legendRoot){
        legendRoot.innerHTML = '';
        const item = document.createElement('div'); item.setAttribute('role','listitem');
        const btn  = document.createElement('button'); btn.type='button'; btn.className='hp-legend-toggle';
        const visible = storageGet('hp_series_visible.'+metricKey,'true')==='true';
        btn.setAttribute('aria-pressed', visible ? 'true':'false');
        btn.textContent = metric;
        btn.addEventListener('click', ()=>{
          const next = !(btn.getAttribute('aria-pressed')==='true');
          btn.setAttribute('aria-pressed', next?'true':'false');
          storageSet('hp_series_visible.'+metricKey, next);
          meta.chart.data.datasets[0].hidden = !next; meta.chart.update();
        });
        item.appendChild(btn); legendRoot.appendChild(item);
        meta.chart.data.datasets[0].hidden = !visible; meta.chart.update();
      }
    }catch(e){}

    CHARTS.push(meta);
    return meta;
  }

  function destroyMeta(meta){
    if(!meta) return;
    try{ if(meta.chart && typeof meta.chart.destroy==='function') meta.chart.destroy(); }catch(e){}
    try{ if(meta.overlay && meta.overlay.parentElement) meta.overlay.parentElement.removeChild(meta.overlay); }catch(e){}
    try{
      const c = meta.canvas;
      if(c){
        const h = meta.handlers||{};
        if(h.onPointerDown) c.removeEventListener('pointerdown', h.onPointerDown);
        if(h.onPointerMove) c.removeEventListener('pointermove', h.onPointerMove);
        if(h.onPointerUp)   c.removeEventListener('pointerup',   h.onPointerUp);
        if(h.onDblClick)    c.removeEventListener('dblclick',    h.onDblClick);
        if(h.onWheel)       c.removeEventListener('wheel',       h.onWheel);
      }
    }catch(e){}
  }

  function applyViewWindowToAll(startTime, endTime){
    if(!startTime || !endTime) return;
    CHARTS.forEach(meta=>{
      const labels = meta.labels;
      const i0 = labels.findIndex(l => l >= startTime);
      let  i1 = labels.map((_,i)=>i).reverse().find(i=> labels[i] <= endTime);
      if(i0 === -1 || i1 === undefined || i1 < i0){
        meta.chart.data.labels = meta.labels.slice();
        meta.chart.data.datasets[0].data = meta.vals.slice();
      } else {
        meta.chart.data.labels = meta.labels.slice(i0, i1+1);
        meta.chart.data.datasets[0].data = meta.vals.slice(i0, i1+1);
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
    if(el._lastRender && (Date.now() - el._lastRender) < 300) return;
    el._lastRender = Date.now();
    while(CHARTS.length){ const m = CHARTS.pop(); try{ destroyMeta(m); }catch(e){} }
    const body = $('.hp-labs-body', el); if(!body) return;
    body.innerHTML = '';
    const row = document.createElement('div'); row.className = 'hp-labs-row';
    (data||[]).forEach(m=>{
      const ctn = makeChartContainer(m.metric);
      const canvas = ctn.querySelector('canvas'); const btn = ctn.querySelector('.hp-export');
      row.appendChild(ctn);
      const labels = (m.series||[]).map(p=> p.t_utc || p.t || '');
      const vals   = (m.series||[]).map(p=> p.v == null ? null : parseFloat(p.v));
      try{ createChart(canvas, m.metric, labels, vals, (m.series||[]), el._hp_current_agg || 'daily'); }catch(e){ console.warn('createChart failed', e); }
      if(btn) btn.addEventListener('click', ()=> _downloadCSV(m.metric, m.series));
    });
    body.appendChild(row);
  }

  async function fetchSeries(person, agg){
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
    if(preferPreview){ const pd = await fetchPreview(person); if(pd){ el._hp_current_agg='preview'; renderCharts(el, pd); return; } }
    try{
      const data = await fetchSeries(person, aggPref);
      el._hp_current_agg = aggPref || 'daily';
      if(!data || data.length === 0){
        const pd = await fetchPreview(person);
        if(pd){ el._hp_current_agg='preview'; renderCharts(el, pd); return; }
        renderEmpty(el); return;
      }
      renderCharts(el, data);
    }catch(e){
      const pd = await fetchPreview(person);
      if(pd){ el._hp_current_agg='preview'; renderCharts(el, pd); return; }
      renderError(el, e);
    }
  }

  function initToolbar(el){
    const toolbar = el.querySelector('.hp-labs-toolbar'); if(!toolbar) return;
    toolbar.innerHTML='';
    const status   = document.createElement('span'); status.style.marginRight='12px'; status.setAttribute('aria-live','polite');
    const scopeSel = document.createElement('select'); scopeSel.innerHTML = '<option value="person">This person</option><option value="global">Global</option>'; scopeSel.style.marginRight='8px';
    const aggSel   = document.createElement('select'); aggSel.innerHTML = '<option value="daily">Daily</option><option value="hourly">Hourly</option>'; aggSel.style.marginRight='8px'; aggSel.setAttribute('aria-label','Aggregation');
    const toggleBtn= document.createElement('button'); toggleBtn.className='hp-export'; toggleBtn.type='button';
    const bandsToggle = document.createElement('button'); bandsToggle.type='button'; bandsToggle.className='hp-bands-toggle'; bandsToggle.textContent='Show reference bands'; bandsToggle.style.marginRight='8px';

    const person = el.getAttribute('data-person-id') || 'global';
    const globalKey='labs_mode_global', personKey=`labs_mode_${person}`, scopeKey='labs_mode_scope';
    scopeSel.value = (localStorage.getItem(scopeKey) || 'person') === 'global' ? 'global' : 'person';
    const aggKey = `hp:labs:agg:${person}`; aggSel.value = localStorage.getItem(aggKey) || (el.getAttribute('data-agg-default') || 'daily');

    function getActiveKey(){ return (scopeSel.value === 'global') ? globalKey : personKey; }
    function getMode(){ return localStorage.getItem(getActiveKey()) || 'live'; }
    function applyMode(mode){
      localStorage.setItem(getActiveKey(), mode); localStorage.setItem(scopeKey, scopeSel.value);
      if(mode === 'live'){
        status.textContent = 'Mode: Live (shows real data)'; toggleBtn.textContent = 'Switch to Preview'; toggleBtn.setAttribute('aria-pressed','false');
        loadWithAgg(el, aggSel.value, false);
      } else {
        status.textContent = 'Mode: Preview (shows sample data)'; toggleBtn.textContent = 'Switch to Live'; toggleBtn.setAttribute('aria-pressed','true');
        fetchPreview(person).then(pd => { if(pd){ el._hp_current_agg='preview'; renderCharts(el, pd); } else { renderEmpty(el); } });
      }
    }

    const bandsKey='hp_bands_enabled'; const bandsEnabled = storageGet(bandsKey,'true')==='true';
    bandsToggle.setAttribute('aria-pressed', bandsEnabled ? 'true' : 'false');
    bandsToggle.addEventListener('click', ()=>{ const cur=bandsToggle.getAttribute('aria-pressed')==='true'; const next=!cur; bandsToggle.setAttribute('aria-pressed', next?'true':'false'); storageSet(bandsKey,next); try{ CHARTS.forEach(m=>{ if(m.chart){ m.chart.config._refBands = next ? REF_BANDS[m.metricKey || canonicalMetric(m.metric)] : null; m.chart.update(); } }); }catch(e){} });

    scopeSel.addEventListener('change', ()=>{ localStorage.setItem(scopeKey, scopeSel.value); applyMode(getMode()); });
    toggleBtn.addEventListener('click', ()=>{ const cur=getMode(); applyMode(cur==='live'?'preview':'live'); });
    aggSel.addEventListener('change', ()=>{ localStorage.setItem(aggKey, aggSel.value); const m=getMode(); if(m==='live'){ loadWithAgg(el, aggSel.value, false); } else { fetchPreview(person).then(pd=>{ if(pd) renderCharts(el,pd); }); } });

    toolbar.appendChild(status); toolbar.appendChild(scopeSel); toolbar.appendChild(aggSel); toolbar.appendChild(bandsToggle); toolbar.appendChild(document.createTextNode(' ')); toolbar.appendChild(toggleBtn);

    applyMode(getMode());
  }

  function boot(){
    document.querySelectorAll(sel).forEach(el=>{
      ensureContainers(el);
      if(!hasChart){ const b=$('.hp-labs-body', el); if(b) b.innerHTML = '<div class="hp-error">Chart.js not loaded — cannot draw charts.</div>'; return; }
      initToolbar(el);
    });
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
