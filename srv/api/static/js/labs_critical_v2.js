/* labs_critical_v2.js – stable load, date-only labels, autoskip ticks */
(function(){
  'use strict';
  const sel = '.hp-labs-critical';
  const $ = (q, el=document) => el.querySelector(q);

  function canonicalMetric(m){ return String(m||'').toLowerCase().replace(/[^a-z0-9]/g,''); }
  function escapeHtml(s){ return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[c]); }
  function storageGet(k,d){ try{ const v=localStorage.getItem(k); return v==null?d:v; }catch(_){ return d; } }
  function storageSet(k,v){ try{ localStorage.setItem(k,String(v)); }catch(_){} }
  function downsample(a,n){ if(!Array.isArray(a)) return a; const L=a.length; if(L<=n) return a.slice(); const s=Math.ceil(L/n); return a.filter((_,i)=>i%s===0); }

  const REF_BANDS = { hr:[{label:'Normal',min:60,max:100}], spo2:[{label:'Healthy',min:94,max:100}] };

  const PREVIEW={key:null,data:null,ts:0,inflight:null,ttl:30000};
  async function fetchPreview(person){
    const k=String(person||''); const now=Date.now();
    if(PREVIEW.key===k && PREVIEW.data && now-PREVIEW.ts<PREVIEW.ttl) return PREVIEW.data;
    if(PREVIEW.inflight) return PREVIEW.inflight;
    PREVIEW.inflight = (async()=>{ try{
      const r=await fetch('/ui/preview/labs/'+encodeURIComponent(k),{cache:'no-store'});
      if(!r.ok) return null; const j=await r.json();
      PREVIEW.key=k; PREVIEW.data=j; PREVIEW.ts=Date.now(); return j;
    }finally{ PREVIEW.inflight=null; }})();
    return PREVIEW.inflight;
  }

  const CHARTS=[];
  function destroyMeta(m){
    if(!m) return;
    try{ m.chart && m.chart.destroy && m.chart.destroy(); }catch(_){}
    try{
      const c=m.canvas, h=m.handlers||{};
      if(c){ ['pointerdown','pointermove','pointerup','dblclick','wheel'].forEach(ev=>{
        if(h['on'+ev.charAt(0).toUpperCase()+ev.slice(1)]) c.removeEventListener(ev, h['on'+ev.charAt(0).toUpperCase()+ev.slice(1)]);
      });}
      if(m.overlay && m.overlay.parentElement) m.overlay.parentElement.removeChild(m.overlay);
    }catch(_){}
  }

  function createChart(canvas, metric, labels, values, rawSeries, agg){
    // labels are date strings ("YYYY-MM-DD") for readability
    const parent = canvas.parentElement || canvas;
    const cssW = parent.clientWidth || 720, cssH = 280;
    const dpr = window.devicePixelRatio || 1;
    canvas.style.width = cssW+'px'; canvas.style.height = cssH+'px';
    canvas.width = Math.max(1, Math.floor(cssW*dpr));
    canvas.height = Math.max(1, Math.floor(cssH*dpr));
    const ctx = canvas.getContext('2d'); ctx.setTransform(dpr,0,0,dpr,0,0);

    const metricKey = canonicalMetric(metric);
    const cfg = {
      type: 'line',
      data: {
        labels: labels.slice(),
        datasets: [{
          label: metric,
          data: values.slice(),
          tension: 0.2,
          pointRadius: 1,
          borderWidth: 2,
          fill: false
        }]
      },
      options: {
        responsive: false,
        maintainAspectRatio: false,
        animation: false,
        interaction: { mode:'nearest', intersect:false },
        plugins: { legend: { display: false } },
        scales: {
          x: {
            grid: { display: true, color:'rgba(0,0,0,0.06)' },
            ticks: {
              autoSkip: true,
              autoSkipPadding: 8,
              maxTicksLimit: 9,
              maxRotation: 0,
              callback: (val) => {
                const s = String(val);         // Chart uses label string directly
                // show "MM-DD" to save space
                return (s.length>=10 ? s.slice(5,10) : s);
              }
            }
          },
          y: {
            beginAtZero: false,
            grid: { color:'rgba(0,0,0,0.06)' }
          }
        }
      }
    };

    // reference band plugin
    const refBands = REF_BANDS[metricKey];
    if(refBands) {
      cfg.plugins = cfg.plugins || {};
      (cfg.plugins.plugins = cfg.plugins.plugins || []).push({
        id:'refBands',
        beforeDatasetsDraw(chart){
          try{
            const y = chart.scales.y, a=chart.chartArea, c=chart.ctx;
            refBands.forEach(b=>{
              if(b.min==null||b.max==null) return;
              const y1=y.getPixelForValue(b.max), y2=y.getPixelForValue(b.min);
              c.save(); c.fillStyle='rgba(34,197,94,0.08)';
              c.fillRect(a.left, y1, a.right-a.left, Math.max(1, y2-y1));
              c.restore();
            });
          }catch(_){}
        }
      });
    }

    // global default color (keeps CSS free of color dependence)
    if (typeof Chart !== 'undefined' && Chart.defaults) {
      Chart.defaults.color = '#3a4a66';
      Chart.defaults.borderColor = 'rgba(0,0,0,0.08)';
    }

    const chart = new Chart(ctx, cfg);
    const meta = { canvas, chart, metric, metricKey, labels: labels.slice(), vals: values.slice(), rawSeries: rawSeries||[], agg: agg||'daily' };
    CHARTS.push(meta);
    return meta;
  }

  function renderEmpty(el){
    const body=$('.hp-labs-body', el);
    body.innerHTML = '<p>No series available.</p>';
  }
  function renderLoading(el){
    const body=$('.hp-labs-body', el);
    body.innerHTML = '<p>Loading…</p>';
  }
  function renderCharts(el, data){
    CHARTS.splice(0).forEach(destroyMeta);
    const body=$('.hp-labs-body', el);
    body.innerHTML='';
    const row=document.createElement('div'); row.className='hp-labs-row';
    (data||[]).forEach(m=>{
      const wrap=document.createElement('div'); wrap.className='hp-labs-chart';
      wrap.innerHTML = '<figure><h4>'+escapeHtml(m.metric)+'</h4><canvas role="img" aria-label="'+escapeHtml(m.metric)+'"></canvas></figure>';
      row.appendChild(wrap);
      const canvas=wrap.querySelector('canvas');

      // DATE-ONLY labels (prefer local if provided)
      const L = (m.series||[]).map(p=> (p.t_local||p.t_utc||p.t||'').toString().slice(0,10));
      const V = (m.series||[]).map(p=> p.v==null?null:Number(p.v));

      try{ createChart(canvas, m.metric, L, V, m.series||[], el._hp_current_agg || 'daily'); }catch(e){ console.warn('chart create failed', e); }
    });
    body.appendChild(row);
  }

  async function fetchSeries(person, agg){
    const u=new URL('/labs/'+encodeURIComponent(person)+'/critical-series', location.origin);
    if(agg) u.searchParams.set('agg', agg);
    u.searchParams.set('metrics', 'hr,spo2');
    const r=await fetch(u.toString(), {cache:'no-store'});
    if(!r.ok) throw r.status; return r.json();
  }

  async function loadWithAgg(el, aggPref, preferPreview){
    const person = el.getAttribute('data-person-id') || '';
    if(!person){ renderEmpty(el); return; }
    renderLoading(el);
    if(preferPreview){
      const pd=await fetchPreview(person); if(pd){ renderCharts(el, pd); return; }
    }
    try{
      const data=await fetchSeries(person, aggPref);
      el._hp_current_agg = aggPref || 'daily';
      if(!data || data.length===0){
        const pd=await fetchPreview(person);
        if(pd){ renderCharts(el,pd); return; }
        renderEmpty(el); return;
      }
      renderCharts(el, data);
    }catch(_){
      const pd=await fetchPreview(person);
      if(pd){ renderCharts(el,pd); return; }
      renderEmpty(el);
    }
  }

  function initToolbar(el){
    const tb = el.querySelector('.hp-labs-toolbar'); if(!tb) return; tb.innerHTML='';
    const status=document.createElement('span'); status.style.marginRight='12px';

    const scopeSel=document.createElement('select'); scopeSel.innerHTML='<option value="person">This person</option><option value="global">Global</option>'; scopeSel.style.marginRight='8px';
    const aggSel=document.createElement('select'); aggSel.innerHTML='<option value="daily">Daily</option><option value="hourly">Hourly</option>'; aggSel.style.marginRight='8px';

    const toggle=document.createElement('button'); toggle.type='button'; toggle.textContent='Switch to Preview';
    const bands=document.createElement('button'); bands.type='button'; bands.className='hp-bands-toggle'; bands.textContent='Show reference bands'; bands.style.marginLeft='8px';

    const person = el.getAttribute('data-person-id') || 'me';
    const scopeKey='labs_mode_scope'; scopeSel.value = localStorage.getItem(scopeKey) || 'person';
    const aggKey=`hp:labs:agg:${person}`; aggSel.value = localStorage.getItem(aggKey) || el.getAttribute('data-agg-default') || 'daily';

    function getModeKey(){ return scopeSel.value==='global'?'labs_mode_global':`labs_mode_${person}`; }
    function applyMode(mode){
      localStorage.setItem(getModeKey(), mode);
      localStorage.setItem(scopeKey, scopeSel.value);
      if(mode==='live'){ status.textContent='Mode: Live (shows real data)'; toggle.textContent='Switch to Preview'; loadWithAgg(el, aggSel.value, false); }
      else { status.textContent='Mode: Preview (shows sample data)'; toggle.textContent='Switch to Live'; fetchPreview(person).then(pd=>pd && renderCharts(el,pd)); }
    }
    function getMode(){ return localStorage.getItem(getModeKey()) || 'live'; }

    scopeSel.addEventListener('change', ()=>applyMode(getMode()));
    aggSel.addEventListener('change', ()=>{ localStorage.setItem(aggKey, aggSel.value); applyMode(getMode()); });
    toggle.addEventListener('click', ()=>applyMode(getMode()==='live'?'preview':'live'));
    bands.addEventListener('click', ()=>{
      const cur = storageGet('hp_bands_enabled','true')==='true'; storageSet('hp_bands_enabled', !cur);
      CHARTS.forEach(m => { if(m.chart){ if(!cur){ m.chart.config._refBands = REF_BANDS[m.metricKey]; } else { m.chart.config._refBands = null; } m.chart.update(); } });
    });

    tb.appendChild(status); tb.appendChild(scopeSel); tb.appendChild(aggSel); tb.appendChild(bands); tb.appendChild(toggle);
    applyMode(getMode());
  }

  function boot(){ document.querySelectorAll(sel).forEach(el => initToolbar(el)); }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
