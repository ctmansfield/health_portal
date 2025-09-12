// language: javascript srv/api/static/js/report_summary_card.js
// Copied from app/static/js/report_summary_card.js for serving via srv/api static mount
(function(){
  'use strict';
  const sel = '.hp-report-summary-card';
  const $ = (q, el=document) => el.querySelector(q);

  function badgeClass(result){
    const r = (result||'').toLowerCase();
    if (r.includes('posi')) return 'badge--positive';
    if (r.includes('nega')) return 'badge--negative';
    return 'badge--inconclusive';
  }

  function render(el, html){
    const body = $('.hp-card-body', el);
    if (body) body.innerHTML = html;
  }

  function renderLoading(el){
    render(el, '<div class="hp-row" role="status" aria-live="polite"><div class="hp-skel"></div></div><div class="hp-skel short"></div>');
  }

  function renderEmpty(el){
    render(el, '<div class="hp-row hp-empty"><strong>No summary available</strong></div>');
  }

  function renderError(el, status){
    const code = status || 'network';
    render(el, `<div class="hp-row"><div class="hp-alert" role="alert">Error loading summary (${code}). <button type="button" class="hp-retry">Retry</button></div></div>`);
    const btn = $('.hp-retry', el);
    if (btn){
      btn.addEventListener('click', () => { btn.disabled = true; load(el).finally(()=>{ btn.disabled = false; btn.focus(); }); });
    }
  }

  function renderSuccess(el, data){
    const when = data && data.signed_out_at ? new Date(data.signed_out_at).toLocaleString() : '—';
    const badge = badgeClass(data && data.result);
    const title = (data && data.title) ? escapeHtml(data.title) : 'Genomic Report';
    const resultText = data && data.result ? escapeHtml(data.result) : '—';
    const id = data && data.id ? encodeURIComponent(data.id) : '';
    const fullHref = id ? `/reports/${id}` : '#';

    render(el, `
      <div class="hp-row">
        <h3 class="hp-title">${title}</h3>
        <span class="hp-badge ${badge}" aria-hidden="true">${resultText}</span>
      </div>
      <div class="hp-row"><span>Signed out</span><span>${escapeHtml(when)}</span></div>
      <div class="hp-row hp-cta"><a href="${fullHref}" ${id ? '' : 'aria-disabled="true" tabindex="-1"'}>View full report</a></div>
    `);
  }

  function escapeHtml(s){
    return String(s).replace(/[&<>"']/g, function(ch){
      return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[ch];
    });
  }

  async function load(el){
    const id = el.getAttribute('data-report-id') || '';
    const apiBase = (el.getAttribute('data-api-base') || '').replace(/\/+$/,'');
    if (!id){
      renderEmpty(el);
      return;
    }
    renderLoading(el);
    const controller = new AbortController();
    const timeout = setTimeout(()=>controller.abort(), 8000);
    try{
      const url = (apiBase || '') + `/reports/${encodeURIComponent(id)}/summary`;
      const res = await fetch(url, { headers: {'Accept':'application/json'}, signal: controller.signal, cache: 'no-store' });
      clearTimeout(timeout);
      if (res.status === 404){
        renderEmpty(el);
        return;
      }
      if (!res.ok){
        try{ console.warn('report_summary_card: fetch failed', { id: id, status: res.status }); }catch(e){}
        renderError(el, res.status);
        return;
      }
      const data = await res.json();
      renderSuccess(el, data || {});
    }catch(e){
      clearTimeout(timeout);
      try{ console.warn('report_summary_card: network error', { id: id }); }catch(e){}
      renderError(el);
    }
  }

  function boot(){
    document.querySelectorAll(sel).forEach(el => { load(el); });
  }

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', boot);
  } else { boot(); }

})();
