document.addEventListener('DOMContentLoaded', function () {
  if (typeof window.loadAndRender === 'function') {
    try { window.loadAndRender(); } catch (e) { console.error('hotfix boot failed', e); }
  }
});
