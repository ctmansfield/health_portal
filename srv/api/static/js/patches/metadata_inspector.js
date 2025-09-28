// Run this in your browser console on the shared labs page
// It fetches current metadata as seen by frontend and logs keys and groups

(function () {
  const controls = document.querySelector('.hp-labs-controls');
  if (!controls) {
    console.warn('Controls container not found');
    return;
  }

  // Find metadata array from your frontend global or state (adjust if needed)
  const meta = window._lastMetadata || null;
  if (!meta) {
    console.warn('Metadata array _lastMetadata not found on window');
    return;
  }

  console.log('Metadata items count:', meta.length);
  if (meta.length > 0) {
    console.log('Sample metadata item keys:', Object.keys(meta[0]));
    const groups = new Set();
    meta.forEach(m => {
      if (m.group) groups.add(m.group);
    });
    console.log('Unique groups found in metadata:', Array.from(groups));
  }
})();
