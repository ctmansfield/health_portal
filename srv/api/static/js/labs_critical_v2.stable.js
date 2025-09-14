// srv/api/static/js/labs_critical_v2.stable.js
// Stable, minimal Labs UI client — no backslash continuations, template literals used.
(function(){
  'use strict';

  const SEL = '.hp-labs-critical';
  const $ = (s, el=document) => el.querySelector(s);

  function escapeHtml(s){ return String(s).replace(/[&<>"']/g, ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[ch]); }
  function canonical(m){ try{ return String(m||'').toLowerCase().replace(/[^a-z0-9]/g,''); }catch(e){ return String(m||''); } }

  const REF_BANDS = { hr:[{label:'Normal',min:60,max:100}], spo2:[{label:'Healthy',min:94,max:100}] };

  function downsample(arr,max=2000){ if(!Array.isArray(arr)) return arr; if(arr.length<=max) return arr.slice(); const step=Math.ceil(arr.length/max); return arr.filter((_,i)=> i % step === 0); }
  function storageGet(k,d){ try{ const v=localStorage.getItem(k); return v==null? d : v; }catch(e){ return d; } }
  function storageSet(k,v){ try{ localStorage.setItem(k,String(v)); }catch(e){} }

  async function fetchPreview(person){
    try{ const res = await fetch('/ui/preview/labs/'+encodeURIComponent(person), {cache:'no-store'}); if(!res.ok) return null; return await res.json(); }catch(e){ console.warn('preview fetch', e); return null; }
  }

  function makeChartContainer(metric){
    const wrapper = document.createElement('div'); wrapper.className='hp-labs-chart';
    wrapper.innerHTML = `
      <figure>
        <h4>${escapeHtml(metric)}</h4>
        <canvas role="img" aria-label="${escapeHtml(metric)} chart"></canvas>
        <figcaption class="hp-caption">Series for ${escapeHtml(metric)}</figcaption>
        <div style="margin-top:8px;display:flex;gap:8px;align-items:center">
          <div class="hp-legend" role="list" aria-label="Series legend"></div>
          <div style="margin-left:auto"><button class="hp-export" type="button">Export CSV</button></div>
        </div>
      </figure>`;
    return wrapper;
  }

  function downloadCSV(filename, csvText){ try{ const blob=new Blob([csvText],{type:'text/csv'}); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download=filename; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);}catch(e){console.warn('downloadCSV',e);} }

  function renderCharts(el, data){
    try{
      const body = $('.hp-labs-body', el); if(!body) return; body.innerHTML='';
      (data||[]).forEach(m=>{
        const ctn = makeChartContainer(m.metric);
        body.appendChild(ctn);
        const canvas = ctn.querySelector('canvas'); if(!canvas) return;
        const labels = (m.series||[]).map(p=> p.t_local || p.t_utc || p.t || '');
        const vals = (m.series||[]).map(p=> p.v==null? null : Number(p.v));
        try{ if(canvas._hp_chart && typeof canvas._hp_chart.destroy==='function') canvas._hp_chart.destroy(); }catch(_){ }
        try{ const ctx = canvas.getContext('2d'); canvas._hp_chart = new Chart(ctx, { type:'line', data:{ labels: labels, datasets:[{ label: m.metric, data: vals, borderColor:'#2563eb', tension:0.2, pointRadius:1, fill:false }] }, options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}} } }); canvas.style.width='100%'; canvas.style.height='240px'; }catch(e){ console.warn('chart create', e); }
        const legendRoot = ctn.querySelector('.hp-legend'); if(legendRoot){ const btn=document.createElement('button'); btn.type='button'; btn.className='hp-legend-toggle'; btn.textContent = m.metric; btn.setAttribute('aria-pressed','true'); btn.addEventListener('click', ()=>{ try{ const ch = canvas._hp_chart; ch.data.datasets[0].hidden = !ch.data.datasets[0].hidden; ch.update(); btn.setAttribute('aria-pressed', ch.data.datasets[0].hidden ? 'false' : 'true'); }catch(e){} }); legendRoot.appendChild(btn); }
      });
    }catch(e){ console.warn('renderCharts error', e); }
  }

  async function init(el){ const person = el.getAttribute('data-person-id') || 'me'; const toolbar = $('.hp-labs-toolbar', el); if(toolbar){ toolbar.innerHTML=''; const agg=document.createElement('select'); agg.innerHTML='<option value="daily">Daily</option><option value="hourly">Hourly</option>'; agg.value = el.getAttribute('data-agg-default') || 'daily'; agg.addEventListener('change', ()=> load(el, agg.value)); const exp=document.createElement('button'); exp.type='button'; exp.textContent='Export CSV (All Visible)'; exp.addEventListener('click', ()=>{ try{ const rows=[['metric','agg','t_utc','t_local','value']]; const csv = rows.map(r=> r.map(c=>'"'+String(c).replace(/"/g,'""')+'"').join(',')).join('\n'); downloadCSV('labs_'+person+'_'+agg.value+'.csv', csv); }catch(e){console.warn(e);} }); toolbar.appendChild(agg); toolbar.appendChild(exp); } await load(el, el.getAttribute('data-agg-default') || 'daily'); }

  async function load(el, agg){ const person = el.getAttribute('data-person-id') || 'me'; const pd = await fetchPreview(person); if(pd && Array.isArray(pd)) renderCharts(el, pd); else { const body = $('.hp-labs-body', el); if(body) body.innerHTML = '<div class="hp-empty">No data</div>'; } }

  function boot(){ document.querySelectorAll(SEL).forEach(el=> init(el)); }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();

})();
