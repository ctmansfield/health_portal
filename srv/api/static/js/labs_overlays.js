(function(){
  'use strict';

  // Medication overlays module

  // Helper to fetch medication events for a person
  async function fetchMedications(personId) {
    try {
      const res = await fetch(`/medications/${encodeURIComponent(personId)}/events`, {cache:'no-store'});
      if(!res.ok) throw new Error('Failed to fetch medications');
      const data = await res.json();
      return data;
    } catch(e) {
      console.warn('Error fetching medications', e);
      return [];
    }
  }

  // Function to add medication overlays to Chart.js chart
  function addMedicationOverlays(chart, medEvents, options={}) {
    if(!chart || !Array.isArray(medEvents)) return;
    const { color='red', label='Medications' } = options;

    // Assuming medEvents is an array of objects with 'time' and 'label' properties
    // Render vertical lines or shaded regions to indicate medication times

    // You will need to integrate a Chart.js plugin or annotation library for better overlays.
    // For now, we can put vertical lines on the x-axis for each medication event.

    // Clear previous overlay plugin if any
    if(chart._medOverlayPlugin) {
      chart._medOverlayPlugin.medEvents = medEvents;
      chart.update();
      return;
    }

    const overlayPlugin = {
      id: 'medOverlay',
      medEvents,
      afterDraw(chart){
        const ctx = chart.ctx;
        const yAxis = chart.scales.y;
        chart._medOverlayPlugin.medEvents.forEach(event => {
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
          ctx.fillText(event.label || '', x + 4, yAxis.top + 10);
          ctx.restore();
        });
      }
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
