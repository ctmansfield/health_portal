(function(){
  'use strict';

  // Common utility functions for labs panels
  const $ = (sel, el=document) => el.querySelector(sel);
  const $$ = (sel, el=document) => Array.from(el.querySelectorAll(sel));

  // Storage helpers
  function storageGet(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : v; } catch(e) { return d; } }
  function storageSet(k, v) { try { localStorage.setItem(k, String(v)); } catch(e) {}
  }

  // Parse ISO 8601-ish date string
  function parseISODate(s) {
    try { return new Date(s); } catch(e) { return null; }
  }

  // Find min and max dates from received lab data
  function getDateRange(data) {
    let minDate = null, maxDate = null;
    if(!data || data.length === 0) {
      const today = new Date();
      minDate = new Date(today.getFullYear(), today.getMonth(), today.getDate());
      maxDate = new Date(minDate);
      return { minDate, maxDate };
    }
    data.forEach(series => {
      if(!series.series) return;
      series.series.forEach(p => {
        const d = parseISODate(p.t_utc);
        if(!minDate || d < minDate) minDate = d;
        if(!maxDate || d > maxDate) maxDate = d;
      });
    });
    return { minDate, maxDate };
  }

  // Make checkbox UI for a metric
  function makeCheckbox(metricKey, label, checked=true){
    const container = document.createElement('div');
    container.style.marginBottom = '6px';
    const cb = document.createElement('input');
    cb.type = 'checkbox'; cb.id = 'cb_' + metricKey; cb.value = metricKey; cb.checked = checked;
    const lbl = document.createElement('label');
    lbl.htmlFor = cb.id;
    lbl.textContent = label;
    lbl.style.marginLeft = '6px';
    container.appendChild(cb); container.appendChild(lbl);
    return container;
  }

  // Make select dropdown for dates
  function makeDateSelect(id, label, date, minDate, maxDate) {
    const container = document.createElement('div');
    container.style.marginRight = '12px';
    const lbl = document.createElement('label');
    lbl.htmlFor = id;
    lbl.textContent = label + ': ';
    lbl.style.marginRight = '4px';
    const select = document.createElement('select');
    select.id = id;

    for(let d = new Date(minDate); d <= maxDate; d.setDate(d.getDate() + 1)) {
      const option = document.createElement('option');
      option.value = d.toISOString().slice(0,10);
      option.textContent = d.toISOString().slice(0,10);
      if(option.value === date) option.selected = true;
      select.appendChild(option);
    }
    container.appendChild(lbl);
    container.appendChild(select);
    return container;
  }

  // Export utilities to global
  window.hpLabsShared = { $, $$, storageGet, storageSet, parseISODate, getDateRange, makeCheckbox, makeDateSelect };
})();
