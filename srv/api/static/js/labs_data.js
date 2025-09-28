(function(){
  'use strict';

  async function fetchAllLabs(personId, startDate, endDate){
    const baseUrl = `/labs/${encodeURIComponent(personId)}/all-series`;
    const params = new URLSearchParams();
    if(startDate) params.set('start_date', startDate);
    if(endDate) params.set('end_date', endDate);
    const url = params.toString() ? `${baseUrl}?${params.toString()}` : baseUrl;
    const r = await fetch(url, { cache: 'no-store' });
    if(!r.ok) {
      const text = await r.text().catch(()=> '');
      console.error('all-series error body:', text);
      throw new Error(`all-series failed: ${r.status}`);
    }
    return r.json();
  }

  async function fetchLabMetadata(personId){
    const baseUrl = `/labs/${encodeURIComponent(personId)}/labs-metadata`;
    const r = await fetch(baseUrl, { cache: 'no-store' });
    if(!r.ok) {
      const text = await r.text().catch(()=> '');
      console.error('labs-metadata error body:', text);
      throw new Error(`labs-metadata failed: ${r.status}`);
    }
    return r.json();
  }

  async function fetchMetricsCatalog(){
    try {
      const r = await fetch('/labs/metrics-catalog', { cache: 'no-store' });
      if (!r.ok) return [];
      return r.json();
    } catch(e) {
      return [];
    }
  }

  window.hpLabsData = { fetchAllLabs, fetchLabMetadata, fetchMetricsCatalog };
})();
