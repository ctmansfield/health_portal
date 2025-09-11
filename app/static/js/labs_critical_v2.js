// labs_critical_v2.js - charts, export, preview toggle with persistent localStorage and scope
(function(){
  'use strict';
  const sel = '.hp-labs-critical';
  const $ = (q, el=document) => el.querySelector(q);

  function escapeHtml(s){ return String(s).replace(/[&<>"']/g, ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[ch]); }

  function makeChartContainer(metric){
    const wrapper = document.createElement('div');
    wrapper.className = 'hp-labs-chart';
    wrapper.innerHTML = `\
      <figure>\
        <h4>${escapeHtml(metric)}</h4>\
        <canvas aria-label="${escapeHtml(metric)} chart" role="img"></canvas>\
        <figcaption class="hp-caption">Series for ${escapeHtml(metric)}. Use the export button to download CSV.</figcaption>\
        <div style="margin-top:8px"><button class="hp-export" type="button">Export CSV</button></div>\
      </figure>`;
    return wrapper;
  }

  function renderLoading(el){ const body = $('.hp-labs-body', el); body.innerHTML=''; const row=document.createElement('div'); row.className='hp-labs-row'; for(let i=0;i<2;i++){const sk=document.createElement('div'); sk.className='hp-labs-skel'; sk.style.width='48%'; row.appendChild(sk);} body.appendChild(row); }
  function renderEmpty(el){ $('.hp-labs-body', el).innerHTML = '<div class="hp-empty">No lab series available</div>'; }
  function renderError(el, status){ $('.hp-labs-body', el).innerHTML = `<div class="hp-error">Error loading labs (${status||'network'})</div>`; }

  function _downloadCSV(metric, series){
    const rows = [['t_utc','t_local','value']];
    series.forEach(p=> rows.push([p.t_utc||p.t||'', p.t_local||'', p.v==null? '': String(p.v)]));
    const csvRows = rows.map(r=> r.map(c => '"' + String(c).replace(/"/g,'""') + '"').join(',')).join('\n');
    const blob = new Blob([csvRows], {type:'text/csv'});
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `${metric.replace(/[^a-z0-9]/gi,'_')}_series.csv`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  }

  function renderCharts(el, data){
    const body = $('.hp-labs-body', el); body.innerHTML=''; const row = document.createElement('div'); row.className='hp-labs-row';
    data.forEach(m=>{
      const ctn = makeChartContainer(m.metric); const canvas = ctn.querySelector('canvas'); const btn = ctn.querySelector('.hp-export'); row.appendChild(ctn);
      const labels = m.series.map(p=> p.t_utc || p.t || ''); const vals = m.series.map(p=> p.v==null?null:parseFloat(p.v));
      try{ new Chart(canvas.getContext('2d'), {type:'line', data:{labels:labels, datasets:[{label:m.metric, data:vals, borderColor:'#2563eb', tension:0.2}]}, options:{plugins:{legend:{display:false}}, scales:{x:{display:true}, y:{beginAtZero:false}}}}); }
      catch(e){ console.warn('chart error', e); }
      if(btn){ btn.addEventListener('click', ()=>_downloadCSV(m.metric, m.series)); }
    });
    body.appendChild(row);
  }

  async function fetchSeries(person){ const res = await fetch(`/labs/${encodeURIComponent(person)}/critical-series?metrics=hr,spo2`, {cache:'no-store'}); if(!res.ok) throw res.status; return res.json(); }
  async function fetchPreview(person){ try{ const res = await fetch(`/ui/preview/labs/${encodeURIComponent(person)}`, {cache:'no-store'}); if(!res.ok) return null; return res.json(); }catch(e){ return null; } }

  async function loadLiveOrPreview(el, preferPreview=false){
    const person = el.getAttribute('data-person-id') || ''; if(!person){ renderEmpty(el); return; }
    renderLoading(el);
    if(preferPreview){ const pd = await fetchPreview(person); if(pd){ renderCharts(el, pd); return; } }
    try{
      const data = await fetchSeries(person);
      if(!data || data.length===0){ const pd = await fetchPreview(person); if(pd){ renderCharts(el, pd); return; } renderEmpty(el); return; }
      renderCharts(el, data);
    }catch(e){ const pd = await fetchPreview(person); if(pd){ renderCharts(el, pd); return; } renderError(el, e); }
  }

  function initToolbar(el){
    const toolbar = el.querySelector('.hp-labs-toolbar'); if(!toolbar) return; toolbar.innerHTML='';
    const status = document.createElement('span'); status.style.marginRight='12px'; status.setAttribute('aria-live','polite');
    const scopeSel = document.createElement('select'); scopeSel.innerHTML = '<option value="person">This person</option><option value="global">Global</option>'; scopeSel.style.marginRight='8px';
    const toggleBtn = document.createElement('button'); toggleBtn.className='hp-export'; toggleBtn.type='button';

    const person = el.getAttribute('data-person-id') || 'global';
    const globalKey = 'labs_mode_global';
    const personKey = `labs_mode_${person}`;
    const scopeKey = 'labs_mode_scope';
    const savedScope = localStorage.getItem(scopeKey) || 'person';
    scopeSel.value = savedScope === 'global' ? 'global' : 'person';

    function getActiveKey(){ return (scopeSel.value === 'global') ? globalKey : personKey; }
    function getMode(){ return localStorage.getItem(getActiveKey()) || (scopeSel.value==='global' ? (localStorage.getItem(personKey)||'live') : (localStorage.getItem(personKey)||'live')); }

    function applyMode(mode){ localStorage.setItem(getActiveKey(), mode); localStorage.setItem(scopeKey, scopeSel.value); if(mode === 'live'){ status.textContent = 'Mode: Live (shows real data)'; toggleBtn.textContent = 'Switch to Preview'; toggleBtn.setAttribute('aria-pressed','false'); loadLiveOrPreview(el, false); } else { status.textContent = 'Mode: Preview (shows sample data)'; toggleBtn.textContent='Switch to Live'; toggleBtn.setAttribute('aria-pressed','true'); fetchPreview(person).then(pd=>{ if(pd) renderCharts(el, pd); }); } }

    // on scope change, reapply mode from target scope
    scopeSel.addEventListener('change', ()=>{ localStorage.setItem(scopeKey, scopeSel.value); const m = getMode(); applyMode(m); });

    toggleBtn.addEventListener('click', ()=>{ const cur = getMode(); applyMode(cur==='live'?'preview':'live'); });

    toolbar.appendChild(status); toolbar.appendChild(scopeSel); toolbar.appendChild(toggleBtn);
    // initialize
    applyMode(getMode());
  }

  function boot(){ document.querySelectorAll(sel).forEach(el=> initToolbar(el)); }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
