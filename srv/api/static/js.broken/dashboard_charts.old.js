// Dashboard charts — stable approach: create charts once, resize on debounced resize
(function(){
  'use strict';

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
    // small fallback if Chart.js missing
    const ctx = cv.getContext('2d');
    ctx.save();
    try{
      ctx.clearRect(0,0,cv.width,cv.height);
      if(!data || data.length === 0) return;
      const len = data.length;
      let min = Infinity, max = -Infinity;
      for(const v of data){ if(v==null) continue; const n=Number(v); if(n<min) min=n; if(n>max) max=n; }
      if(min === Infinity || max === -Infinity){ min=0; max=1; }
      const span = (max===min) ? (max||1) : (max-min);
      ctx.beginPath();
      ctx.lineWidth = Math.max(1, Math.round(2 * (window.devicePixelRatio||1)));
      ctx.strokeStyle = color || '#2563eb';
      for(let i=0;i<len;i++){
        const x = Math.round((i/(len-1)) * cv.width);
        const v = data[i]==null?null:Number(data[i]);
        const y = (v==null) ? cv.height/2 : Math.round(cv.height - ((v - min)/span) * cv.height);
        if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
      }
      ctx.stroke();
      if(fill){ ctx.globalAlpha = 0.06; ctx.lineTo(cv.width, cv.height); ctx.lineTo(0, cv.height); ctx.closePath(); ctx.fillStyle = color || '#2563eb'; ctx.fill(); ctx.globalAlpha = 1; }
    }catch(e){}
    ctx.restore();
  }

  function createChartOnce(cv, config){
    try{ if(cv._chartInstance && typeof cv._chartInstance.destroy === 'function') cv._chartInstance.destroy(); }catch(e){}
    const ctx = cv.getContext('2d');
    if(window.Chart){
      try{
        cv._chartInstance = new Chart(ctx, config);
      }catch(e){
        fallbackDraw(cv, (config.data&&config.data.datasets&&config.data.datasets[0]&&config.data.datasets[0].data) || [], (config.data&&config.data.datasets&&config.data.datasets[0]&&config.data.datasets[0].borderColor) || null, true);
      }
    } else {
      fallbackDraw(cv, (config.data&&config.data.datasets&&config.data.datasets[0]&&config.data.datasets[0].data) || [], (config.data&&config.data.datasets&&config.data.datasets[0]&&config.data.datasets[0].borderColor) || null, true);
    }
  }

  function initCharts(){
    // expose arrays (should already be set by template)
    window.hrLabels = window.hrLabels || [];
    window.hrData = window.hrData || [];
    window.spo2Data = window.spo2Data || [];

    // ensure canvases sized and create charts once
    const hrCanvas = document.querySelector('.chart-wrap canvas#hrDaily') || document.querySelector('.chart-wrap canvas');
    if(hrCanvas){
      sizeCanvas(hrCanvas);
      createChartOnce(hrCanvas, {
        type: 'line',
        data: { labels: window.hrLabels, datasets: [{ label: 'Median HR', data: window.hrData, borderColor: 'rgb(37,99,235)', backgroundColor: 'rgba(37,99,235,0.08)', tension: 0.2 }] },
        options: { responsive: false, maintainAspectRatio: false, interaction:{mode:'nearest',intersect:false}, plugins:{legend:{display:false}}, scales:{ y:{ beginAtZero:false }}}
      });
    }

    const spo2Canvas = document.getElementById('spo2Chart');
    if(spo2Canvas){
      sizeCanvas(spo2Canvas);
      createChartOnce(spo2Canvas, {
        type: 'line',
        data: { labels: window.hrLabels, datasets: [{ label: 'Min SpO2', data: window.spo2Data, borderColor: 'rgb(14,165,233)', backgroundColor: 'rgba(14,165,233,0.06)', tension: 0.2 }] },
        options: { responsive: false, maintainAspectRatio: false, interaction:{mode:'nearest',intersect:false}, plugins:{legend:{display:false}}, scales:{ y:{ beginAtZero:true, suggestedMax:1.0 }}}
      });
    }

    // sparklines
    const hrSpark = document.getElementById('hrSpark');
    if(hrSpark){ sizeCanvas(hrSpark); createChartOnce(hrSpark, { type:'line', data:{ labels: window.hrLabels, datasets:[{ data: window.hrData, borderColor:'rgb(37,99,235)', fill:false }] }, options:{ responsive:false, maintainAspectRatio:false, plugins:{legend:{display:false}}, elements:{point:{radius:0}}, scales:{x:{display:false},y:{display:false}} } }); }

    const spo2Spark = document.getElementById('spo2Spark');
    if(spo2Spark){ sizeCanvas(spo2Spark); createChartOnce(spo2Spark, { type:'line', data:{ labels: window.hrLabels, datasets:[{ data: window.spo2Data, borderColor:'rgb(14,165,233)', fill:false }] }, options:{ responsive:false, maintainAspectRatio:false, plugins:{legend:{display:false}}, elements:{point:{radius:0}}, scales:{x:{display:false},y:{display:false}} } }); }
  }

  // Debounced resize: resize backing store and call chart.resize()
  function onResizeDebounced(){
    let timer = null;
    function handler(){
      if(timer) clearTimeout(timer);
      timer = setTimeout(()=>{
        // size canvases, then call chart.resize/update where present
        document.querySelectorAll('.chart-wrap canvas, #spo2Chart, #hrSpark, #spo2Spark').forEach(cv=>{
          const ctx = sizeCanvas(cv);
          try{
            if(cv._chartInstance){ cv._chartInstance.resize(); cv._chartInstance.update(); }
          }catch(e){}
        });
        timer = null;
      }, 150);
    }
    window.addEventListener('resize', handler);
    window.addEventListener('orientationchange', handler);
  }

  function waitForChart(cb){
    if(window.Chart) return cb();
    const to = setInterval(()=>{ if(window.Chart){ clearInterval(to); cb(); } }, 50);
    setTimeout(()=>{ clearInterval(to); cb(); }, 5000);
  }

  document.addEventListener('DOMContentLoaded', function(){
    waitForChart(function(){
      initCharts();
      onResizeDebounced();
    });
  });
})();
EOF
