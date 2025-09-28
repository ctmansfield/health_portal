(function(){
  'use strict';

  // Medication overlays module

  // Helper to fetch medication events for a person
  async function fetchMedications(personId) {
    try {
      const res = await fetch(`/medications/${encodeURIComponent(personId)}/events`, {
        cache:'no-store',
        credentials: 'include'
      });
      if (!res.ok) {
        if (res.status === 401 || res.status === 403) {
          // Not authenticated; silently skip overlays
          return [];
        }
        throw new Error(`Failed to fetch medications: ${res.status}`);
      }
      const data = await res.json();
      return data;
    } catch(e) {
      // Reduce console noise; overlay is optional
      console.debug('Medication overlays unavailable:', e && e.message ? e.message : e);
      return [];
    }
  }

  // Function to add medication overlays to Chart.js chart
  function addMedicationOverlays(chart, medEvents, options = {}) {
    if (!chart || !Array.isArray(medEvents)) return;
    const { color = 'red', label = 'Medications' } = options;

    // Defensive: do not set plugins directly; check if plugins array is accessible
    if (!Array.isArray(chart.config.plugins)) {
      console.warn('Chart.js plugins array unavailable, skipping adding medication overlays');
      return;
    }

    // Check if overlay plugin already exists
    if (chart._medOverlayPlugin) {
      chart._medOverlayPlugin.medEvents = medEvents;
      chart.update();
      return;
    }

    const overlayPlugin = {
      id: 'medOverlay',
      medEvents,
      afterDraw(chart) {
        const ctx = chart.ctx;
        const yAxis = chart.scales.y;
        if (!chart._medOverlayPlugin.medEvents) return;
        chart._medOverlayPlugin.medEvents.forEach((event) => {
          if (!event.time) return; // defensive
          const xScale = chart.scales.x;
          const x = xScale.getPixelForValue(event.time);
          ctx.save();
          ctx.strokeStyle = color;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(x, yAxis.top);
          ctx.lineTo(x, yAxis.bottom);
          ctx.stroke();
          ctx.fillStyle = color;
          ctx.font = '10px Arial';
          const label = event.label || '';
          ctx.fillText(label, x + 4, yAxis.top + 10);
          ctx.restore();
        });
      },
  };

    chart._medOverlayPlugin = overlayPlugin;
    chart.config.plugins.push(overlayPlugin);
    chart.update();
  }

  window.hpLabsOverlays = {
    fetchMedications,
    addMedicationOverlays
  };

})();
