(function(){
  'use strict';
  if(window.__hp_labs_critical_loaded) return; window.__hp_labs_critical_loaded = true;
  const SEL = '.hp-labs-critical';
  const $ = (s, el=document) => el.querySelector(s);
  async function fetchPreview(person){ try{ const res = await fetch('/ui/preview/labs/'+encodeURIComponent(person), {cache:'no-store'}); if(!res.ok) return null; return await res.json(); }catch(e){return null;} }
  function makeChartContainer(metric){ const w=document.createElement('div'); w.className='hp-labs-chart'; w.innerHTML='<figure><h4>'+String(metric)+'</h4><canvas role="img" aria-label="'+String(metric)+' chart"></canvas><figcaption class="hp-caption">Series for '+String(metric)+'</figcaption></figure>'; return w; }
  async function init(el){ try{ const person = el.getAttribute('data-person-id') || 'me'; const pd = await fetchPreview(person); const body = $('.hp-labs-body', el); if(!body) return; body.innerHTML=''; (pd||[]).forEach(m=> body.appendChild(makeChartContainer(m.metric))); }catch(e){ console.warn('labs safe init', e); } }
  function boot(){ document.querySelectorAll(SEL).forEach(el=> init(el)); }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
