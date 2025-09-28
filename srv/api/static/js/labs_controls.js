(function(){
  'use strict';

  const { $, storageGet, storageSet, getDateRange, makeDateSelect } = window.hpLabsShared;

  function updateDateSelectors(el, minDate, maxDate, start, end) {
    const controls = $('.hp-labs-controls', el);
    if (!controls) return;
    // Find existing selects' container (we assume first child is the date container if exists)
    let dateRangeContainer = controls.querySelector('.hp-date-range');
    if (!dateRangeContainer) {
      dateRangeContainer = document.createElement('div');
      dateRangeContainer.className = 'hp-date-range';
      dateRangeContainer.style.display = 'flex';
      dateRangeContainer.style.alignItems = 'center';
      dateRangeContainer.style.gap = '8px';
      controls.prepend(dateRangeContainer);
    } else {
      dateRangeContainer.innerHTML = '';
    }
    const startSel = makeDateSelect('shared_labs_start_date', 'Start Date', start, minDate, maxDate);
    const endSel = makeDateSelect('shared_labs_end_date', 'End Date', end, minDate, maxDate);
    dateRangeContainer.appendChild(startSel);
    dateRangeContainer.appendChild(endSel);
  }

  function buildGroupsFromMetadata(metadata) {
    const HIDDEN_PANELS = new Set(['drug screen', 'sti tests']);
    const panelMap = {};
    (metadata || []).forEach(m => {
      const panel = (m.group_name || m.group || 'Other').toLowerCase();
      if (HIDDEN_PANELS.has(panel)) return;
      if (!panelMap[panel]) panelMap[panel] = [];
      panelMap[panel].push(m);
    });
    return panelMap;
  }

  function renderControls(el, series, metadata, onChange, initialChecked = []) {
    const controls = $('.hp-labs-controls', el);
    controls.innerHTML = '';

    // Date controls if series present (initial)
    if (series && series.length) {
      const { minDate, maxDate } = getDateRange(series);
      const storedStart = storageGet('shared_labs_date_start', minDate.toISOString().slice(0, 10));
      const storedEnd = storageGet('shared_labs_date_end', maxDate.toISOString().slice(0, 10));
      // Use a dedicated container so we can update later without rebuilding whole controls
      const dateRangeContainer = document.createElement('div');
      dateRangeContainer.className = 'hp-date-range';
      dateRangeContainer.style.display = 'flex';
      dateRangeContainer.style.alignItems = 'center';
      dateRangeContainer.style.gap = '8px';
      dateRangeContainer.appendChild(makeDateSelect('shared_labs_start_date', 'Start Date', storedStart, minDate, maxDate));
      dateRangeContainer.appendChild(makeDateSelect('shared_labs_end_date', 'End Date', storedEnd, minDate, maxDate));
      controls.appendChild(dateRangeContainer);
    }

    const panelMap = buildGroupsFromMetadata(metadata);
    const panels = Object.keys(panelMap).sort((a,b) => (a==='other') - (b==='other') || a.localeCompare(b));

    const panelSelector = document.createElement('select');
    panelSelector.style.margin = '8px 0';
    panels.forEach(panel => {
      const option = document.createElement('option');
      option.value = panel;
      option.textContent = panel.charAt(0).toUpperCase() + panel.slice(1);
      panelSelector.appendChild(option);
    });
    controls.appendChild(panelSelector);

    const checkboxContainer = document.createElement('div');
    controls.appendChild(checkboxContainer);

    function renderCheckboxes(panel) {
      checkboxContainer.innerHTML = '';
      const labs = (panelMap[panel] || []).slice().sort((a,b)=> (a.label||a.metric).localeCompare(b.label||b.metric));
      labs.forEach(item => {
        const row = document.createElement('div');
        row.style.display = 'flex'; row.style.alignItems = 'center'; row.style.marginBottom = '6px';
        const cb = document.createElement('input');
        cb.type = 'checkbox'; cb.value = item.metric || item; cb.id = 'cb_' + cb.value; cb.checked = initialChecked.includes(cb.value);
        const lbl = document.createElement('label');
        const count = (item.series_count != null) ? ` (${item.series_count})` : '';
        lbl.htmlFor = cb.id; lbl.textContent = (item.label || cb.value) + count; lbl.style.marginLeft = '8px';
        row.appendChild(cb); row.appendChild(lbl);
        checkboxContainer.appendChild(row);
      });
    }

    panelSelector.addEventListener('change', () => { renderCheckboxes(panelSelector.value); if (onChange) onChange('panel-change'); });

    if (panels.length > 0) renderCheckboxes(panels[0]);

    controls.addEventListener('change', (e) => {
      if (e.target.type === 'checkbox') {
        // Persist currently selected metrics for convenience
        const selected = Array.from(controls.querySelectorAll('input[type=checkbox]:checked')).map(cb => cb.value);
        try { storageSet('shared_labs_selected_metrics', selected.join(',')); } catch(e) {}
        if (onChange) onChange('checkbox');
      } else if (e.target.tagName === 'SELECT' && e.target !== panelSelector) {
        if (onChange) onChange('date');
      } else if (e.target.id === 'shared_labs_start_date' || e.target.id === 'shared_labs_end_date') {
        if (onChange) onChange('date');
      }
    });
  }

  function getSelectedMetrics(el) {
    return Array.from(el.querySelectorAll('.hp-labs-controls input[type=checkbox]:checked')).map(cb => cb.value.toLowerCase());
  }

  window.hpLabsControls = { renderControls, getSelectedMetrics, updateDateSelectors };

})();
