// Patch for chartjs-plugin-zoom to add passive: true option to wheel event listener
if (window.Chart && window.Chart.Zoom) {
  const origAddEventListener = window.Chart.Zoom._addWheelListener;
  window.Chart.Zoom._addWheelListener = function(element, callback, passive) {
    origAddEventListener.call(this, element, callback, { passive: true });
  };
}
