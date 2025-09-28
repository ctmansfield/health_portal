(function(){
  'use strict';

  const SEL = '.hp-labs-shared';
  const { $, storageGet, storageSet, getDateRange } = window.hpLabsShared;
  const { fetchAllLabs, fetchLabMetadata } = window.hpLabsData;
  const { renderControls, getSelectedMetrics } = window.hpLabsControls;
  const { renderCharts } = window.hpLabsCharts;
  const { fetchMedications } = window.hpLabsOverlays || { fetchMedications: async ()=>[] };

  function showError(msg) {
    const el = document.querySelector('#labs-shared-error');
    if (el) { el.textContent = msg; el.classList.remove('hidden'); }
    else { console.error(msg); }
  }

  async function loadAndRender(el){
    const personId = (el && el.dataset && el.dataset.personId) ? el.dataset.personId : 'me';

    let series = [];
    let metadata = [];
    let medEvents = [];

    try {
      metadata = await fetchLabMetadata(personId);
    } catch(e){
      console.warn('labs-metadata failed', e);
      metadata = [];
    }

    try {
      // Fetch full range first to derive default date range
      series = await fetchAllLabs(personId);
      const { minDate, maxDate } = getDateRange(series);
      // Always default to full available range on boot
      let start = minDate.toISOString().slice(0,10);
      let end = maxDate.toISOString().slice(0,10);
      storageSet('shared_labs_date_start', start);
      storageSet('shared_labs_date_end', end);
      // Refetch constrained range based on the full bounds
      series = await fetchAllLabs(personId, start, end);
      // After we have constrained series, update the date controls to reflect exact min/max
      const { updateDateSelectors } = window.hpLabsControls;
      if (updateDateSelectors) {
        const elMinMax = getDateRange(series);
        updateDateSelectors(el, elMinMax.minDate, elMinMax.maxDate, start, end);
      }
    } catch(e){
      console.error('all-series failed', e);
      showError('Could not load lab series. Please retry.');
      return;
    }

    try {
      medEvents = await fetchMedications(personId);
    } catch(e){
      medEvents = [];
    }

    // Default select a small initial set (first 3 metrics with data) for quick visibility
    const metricsWithData = (series || []).filter(s => (s.series || []).length > 0).map(s => s.metric);
    const initialChecked = metricsWithData.slice(0, 3);

    // Initial controls and charts
    renderControls(el, series, metadata, async (reason) => {
      if (reason === 'date') {
        const startEl = document.getElementById('shared_labs_start_date');
        const endEl = document.getElementById('shared_labs_end_date');
        if (startEl && endEl) {
          const start = startEl.value;
          const end = endEl.value;
          if (start > end) { return; }
          storageSet('shared_labs_date_start', start);
          storageSet('shared_labs_date_end', end);
          try {
            series = await fetchAllLabs(personId, start, end);
            // Update the date control bounds to reflect min/max in this selection
            const { updateDateSelectors } = window.hpLabsControls;
            if (updateDateSelectors) {
              const elMinMax = getDateRange(series);
              updateDateSelectors(el, elMinMax.minDate, elMinMax.maxDate, start, end);
            }
          } catch (e) {
            console.error('all-series (date change) failed', e);
          }
        }
      }
      renderCharts(el, series, medEvents);
    }, initialChecked);

    // Render once after controls created so initialChecked take effect
    renderCharts(el, series, medEvents);
  }

  function boot(){
    document.querySelectorAll(SEL).forEach(el => loadAndRender(el));
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
