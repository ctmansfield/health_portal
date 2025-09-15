(function(){
  async function fetchJSON(url, opts) {
    opts = opts || {};
    var controller = new AbortController();
    var timeoutMs = (opts.timeoutMs != null) ? opts.timeoutMs : 15000;
    var id = setTimeout(function(){ try{ controller.abort(); }catch(e){} }, timeoutMs);
    try {
      var r = await fetch(url, { signal: controller.signal, cache: 'no-store' });
      if (!r.ok) {
        var text = '';
        try { text = await r.text(); } catch (_){}
        throw new Error(url + ' ' + r.status + ' ' + (text || ''));
      }
      return await r.json();
    } finally {
      clearTimeout(id);
    }
  }

  function showError(msg) {
    var el = document.querySelector('#labs-shared-error');
    if (el) { el.textContent = msg; el.classList.remove('hidden'); }
    else { console.error(msg); }
  }

  var orig = (typeof window !== 'undefined' && typeof window.loadAndRender === 'function') ? window.loadAndRender : null;

  async function safeLoadAndRender(){
    try {
      var results = await Promise.allSettled([
        fetchJSON('/labs/me/all-series'),
        fetchJSON('/labs/me/labs-metadata')
      ]);
      var seriesOk = results[0].status === 'fulfilled';
      var metaOk = results[1].status === 'fulfilled';
      if (!seriesOk) {
        console.error('Error loading shared labs series:', results[0].reason);
        showError('Could not load lab series. Please retry.');
        return;
      }
      var series = results[0].value;
      var meta = metaOk ? results[1].value : {};
      if (!metaOk) {
        console.warn('Labs metadata unavailable, rendering without it:', results[1].reason);
      }
      try {
        if (typeof renderGraphs === 'function') {
          renderGraphs(series, meta);
        } else if (orig) {
          await orig();
        } else {
          console.error('renderGraphs() not found');
          showError('Unable to render lab graphs.');
        }
      } catch (e) {
        console.error('Render error:', e);
        showError('Unable to render lab graphs.');
      }
    } catch (err) {
      console.error('loadAndRender failed:', err);
      if (orig) { try { await orig(); } catch(_){} }
    }
  }

  window.loadAndRender = safeLoadAndRender;
})();
