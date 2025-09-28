// Robust fallback: force passive:true for 'wheel' listeners attached to canvas to silence Chrome scroll-blocking warnings.
(function(){
  try {
    const ET = EventTarget.prototype;
    const _add = ET.addEventListener;
    ET.addEventListener = function(type, listener, options){
      try {
        if (type === 'wheel') {
          // Only affect canvas to avoid breaking other UI that relies on preventDefault
          const isCanvas = (this && (this.tagName === 'CANVAS' || this.classList && this.classList.contains('chartjs-render-monitor')));
          if (isCanvas) {
            // Normalize options
            if (options === undefined) {
              options = { passive: true };
            } else if (typeof options === 'boolean') {
              options = { capture: options, passive: true };
            } else if (typeof options === 'object' && options.passive == null) {
              options = { ...options, passive: true };
            }
          }
        }
      } catch (e) { /* noop */ }
      return _add.call(this, type, listener, options);
    };
  } catch(e) {
    // ignore
  }
})();
