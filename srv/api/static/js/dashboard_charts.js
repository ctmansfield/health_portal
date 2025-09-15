// fixed dashboard charts — create charts once using canvas element, DPR-safe sizing, debounced resize
(function(){
  'use strict';

  // Import medication overlay helpers from global hpLabsOverlays (loaded before this script via script tag)
  const { fetchMedications, addMedicationOverlays } = window.hpLabsOverlays || {};

  // Add test medication events for overlay testing
  const TEST_MED_EVENTS = [
    { time: '2023-12-06T00:00:00Z', label: 'Testosterone 150mg/week' },
    { time: '2022-02-26T00:00:00Z', label: 'Lisinopril 10mg' },
    { time: '2022-04-14T00:00:00Z', label: 'Lisinopril 20mg' },
    { time: '2023-06-15T00:00:00Z', label: 'Lisinopril 80mg daily' },
    { time: '2024-07-01T00:00:00Z', label: 'Lisinopril discontinued' },
    { time: '2025-03-06T00:00:00Z', label: 'Lisinopril resumed 40mg daily' },
    { time: '2025-05-06T00:00:00Z', label: 'Lisinopril stopped' }
  ];

  async function addMedOverlaysToAllCharts(medEvents){
    if(!medEvents || medEvents.length === 0) return;
      document.querySelectorAll('.chart-wrap canvas, #spo2Chart, #hrSpark, #spo2Spark').forEach(cv=>{
      if(cv && cv._chart) addMedicationOverlays(cv._chart, medEvents, { color: '#4ade80', label: 'Medications' });
      });
  }

  function sizeCanvas(canvas){
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.parentElement.getBoundingClientRect();
    const targetW = Math.max(1, Math.round(rect.width * dpr));
    const targetH = Math.max(1, Math.round(rect.height * dpr));
    if(canvas.width !== targetW || canvas.height !== targetH){
      canvas.width = targetW;
      canvas.height = targetH;
    }
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr,0,0,dpr,0,0);
    return ctx;
  }

  function fallbackDraw(cv, data, color, fill){
    const ctx = cv.getContext('2d');
    ctx.save();
    try{
      ctx.clearRect(0,0,cv.width,cv.height);
      if(!data || data.length === 0) return;
      const len = data.length; let min=Infinity, max=-Infinity;
      for(const v of data){ if(v==null) continue; const n=Number(v); if(n<min) min=n; if(n>max) max=n; }
      if(min===Infinity||max===-Infinity){ min=0; max=1; }
      const span = (max===min)?(max||1):(max-min);
      ctx.beginPath(); ctx.lineWidth = Math.max(1, Math.round(2*(window.devicePixelRatio||1)));
      ctx.strokeStyle = color || '#2563eb';
      for(let i=0;i<len;i++){
        const x=Math.round((i/(len-1))*cv.width);
        const v=data[i]==null?null:Number(data[i]);
        const y=(v==null)?(cv.height/2):Math.round(cv.height-((v-min)/span)*cv.height);
        if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
      }
      ctx.stroke();
      if(fill){
        ctx.globalAlpha=0.06;
        ctx.lineTo(cv.width,cv.height);
        ctx.lineTo(0,cv.height);
        ctx.closePath();
        ctx.fillStyle=color||'#2563eb';
        ctx.fill();
        ctx.globalAlpha=1;
      }
    }catch(e){}
    ctx.restore();
  }

  function createChart(cv, cfg){
    try{ if(cv._chart && typeof cv._chart.destroy === 'function') cv._chart.destroy(); }catch(e){}
    if(window.Chart){
      try{ cv._chart = new Chart(cv, cfg); }catch(e){ fallbackDraw(cv, (cfg.data && cfg.data.datasets && cfg.data.datasets[0] && cfg.data.datasets[0].data) || [], (cfg.data && cfg.data.datasets && cfg.data.datasets[0] && cfg.data.datasets[0].borderColor) || null, true); }
    } else {
      fallbackDraw(cv, (cfg.data && cfg.data.datasets && cfg.data.datasets[0] && cfg.data.datasets[0].data) || [], (cfg.data && cfg.data.datasets && cfg.data.datasets[0] && cfg.data.datasets[0].borderColor) || null, true);
    }
  }

  async function initChartsOnce(){
    window.hrLabels = window.hrLabels || [];
    window.hrData = window.hrData || [];
    window.spo2Data = window.spo2Data || [];

    const hrCv = document.querySelector('.chart-wrap canvas#hrDaily') || document.querySelector('.chart-wrap canvas');
    if(hrCv){ sizeCanvas(hrCv); createChart(hrCv, { type:'line', data:{ labels: window.hrLabels, datasets:[{ label:'Median HR', data: window.hrData, borderColor:'rgb(37,99,235)', backgroundColor:'rgba(37,99,235,0.08)', tension:0.2 }] }, options:{ responsive:false, maintainAspectRatio:false, interaction:{mode:'nearest',intersect:false}, plugins:{legend:{display:false}}, scales:{y:{beginAtZero:false}} } }); }

    const spo2Cv = document.getElementById('spo2Chart');
    if(spo2Cv){ sizeCanvas(spo2Cv); createChart(spo2Cv, { type:'line', data:{ labels: window.hrLabels, datasets:[{ label:'Min SpO2', data: window.spo2Data, borderColor:'rgb(14,165,233)', backgroundColor:'rgba(14,165,233,0.06)', tension:0.2 }] }, options:{ responsive:false, maintainAspectRatio:false, interaction:{mode:'nearest',intersect:false}, plugins:{legend:{display:false}}, scales:{y:{beginAtZero:true,suggestedMax:1.0}} } }); }

    const hrSpark = document.getElementById('hrSpark'); if(hrSpark){ sizeCanvas(hrSpark); createChart(hrSpark, { type:'line', data:{ labels: window.hrLabels, datasets:[{ data: window.hrData, borderColor:'rgb(37,99,235)', backgroundColor:'rgba(37,99,235,0.06)', fill:true }] }, options:{ responsive:false, maintainAspectRatio:false, interaction:{mode:'nearest',intersect:false}, hover:{mode:'nearest',intersect:false}, events:['mousemove','mouseout','click','touchstart','touchmove'], plugins:{legend:{display:false}, tooltip:{enabled:true, mode:'nearest', intersect:false}}, animation:false, elements:{point:{radius:0, hitRadius:6}}, scales:{x:{display:false},y:{display:false}} } }); }
    const spo2Spark = document.getElementById('spo2Spark'); if(spo2Spark){ sizeCanvas(spo2Spark); createChart(spo2Spark, { type:'line', data:{ labels: window.hrLabels, datasets:[{ data: window.spo2Data, borderColor:'rgb(14,165,233)', backgroundColor:'rgba(14,165,233,0.06)', fill:true }] }, options:{ responsive:false, maintainAspectRatio:false, interaction:{mode:'nearest',intersect:false}, plugins:{legend:{display:false}, tooltip:{enabled:true, mode:'nearest', intersect:false}}, elements:{point:{radius:0, hitRadius:6}}, scales:{x:{display:false},y:{display:false}} } }); }

    // fetch medications and add overlays after charts created
    if(typeof fetchMedications === 'function' && typeof addMedicationOverlays === 'function' && window.personId){
      try {
        const medEvents = await fetchMedications(window.personId);
        // Merge test events with fetched events
        const mergedEvents = [...medEvents, ...TEST_MED_EVENTS];

        // Filter valid med events
        const validMedEvents = mergedEvents.filter(e => e && typeof e.time === 'string' && typeof e.label === 'string');
        await addMedOverlaysToAllCharts(validMedEvents);
      } catch(e) {
        console.warn('Failed to load medication overlays', e);
      }
    }
  }

  function onResize(){
    if(window.__hp_resize_timer) clearTimeout(window.__hp_resize_timer);
    window.__hp_resize_timer = setTimeout(()=>{
      document.querySelectorAll('.chart-wrap canvas, #spo2Chart, #hrSpark, #spo2Spark').forEach(cv=>{
        try{ sizeCanvas(cv); if(cv._chart){ cv._chart.resize(); cv._chart.update(); } }catch(e){}
      });
      window.__hp_resize_timer = null;
    }, 150);
  }

  function waitForChart(cb){ if(window.Chart) return cb(); const to=setInterval(()=>{ if(window.Chart){ clearInterval(to); cb(); } },50); setTimeout(()=>{ clearInterval(to); cb(); },5000); }

  // expose helpers for debugging/manual init
  window.hpInitCharts = initChartsOnce;
  window.hpRedraw = function(){ try{ redrawAll(); }catch(e){} };

  document.addEventListener('DOMContentLoaded', function(){ waitForChart(function(){ initChartsOnce(); window.addEventListener('resize', onResize); window.addEventListener('orientationchange', onResize); }); });

})();
