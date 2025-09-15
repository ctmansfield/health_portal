(function(){
  'use strict';

  async function fetchEvents(){
    try {
      const res = await fetch('/dashboard/events.json', {cache:'no-store'});
      if(!res.ok) throw new Error('Failed to fetch events');
      return await res.json();
    } catch(e) {
      console.warn('Error fetching events', e);
      return [];
    }
  }

  function renderEventsTable(events){
    const container = document.getElementById('eventsRoot');
    if(!container) return;
    if(events.length === 0){
      container.innerHTML = '<p>No recent events.</p>';
      return;
    }

    const table = document.createElement('table');
    table.style.width = '100%';
    table.style.borderCollapse = 'collapse';

    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    ['Time', 'Metric', 'Level', 'Score', 'Context'].forEach(text => {
      const th = document.createElement('th');
      th.textContent = text;
      th.style.border = '1px solid #ccc';
      th.style.padding = '8px';
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    events.forEach(evt => {
      const row = document.createElement('tr');
      ['finding_time', 'metric', 'level', 'score', 'context'].forEach(field => {
        const td = document.createElement('td');
        td.textContent = evt[field] || '';
        td.style.border = '1px solid #ccc';
        td.style.padding = '8px';
        row.appendChild(td);
      });
      tbody.appendChild(row);
    });

    table.appendChild(tbody);
    container.innerHTML = '';
    container.appendChild(table);
  }

  async function boot() {
    const events = await fetchEvents();
    renderEventsTable(events);
  }

  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

})();
