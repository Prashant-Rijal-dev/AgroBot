/* AgroBot — Dashboard JS */

const METRIC_CONFIG = {
  moisture:    { label: 'Moisture (%)',     color: '#0ea5e9', low: 40,  high: 80   },
  temperature: { label: 'Temperature (°C)', color: '#ef4444', low: 10,  high: 35   },
  ph:          { label: 'pH',               color: '#8b5cf6', low: 5.5, high: 7.5  },
  nitrogen:    { label: 'Nitrogen (mg/kg)', color: '#10b981', low: 30,  high: null },
};

let chart = null;
let currentMetric = 'moisture';
let historyData = [];

/* ---- Fetch history & render chart ---- */
async function loadChart(metric) {
  currentMetric = metric;
  try {
    const res = await fetch('/api/sensor/history?hours=24');
    if (!res.ok) return;
    historyData = await res.json();
    renderChart(metric);
  } catch (e) {
    console.error('Chart load failed:', e);
  }
}

function renderChart(metric) {
  const cfg  = METRIC_CONFIG[metric];
  const ctx  = document.getElementById('trendChart');
  if (!ctx || !historyData.length) return;

  const labels = historyData.map(r => r.timestamp);
  const values = historyData.map(r => r[metric]);

  if (chart) chart.destroy();

  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: cfg.label,
        data: values,
        borderColor: cfg.color,
        backgroundColor: cfg.color + '22',
        borderWidth: 2.5,
        pointRadius: 0,
        pointHoverRadius: 5,
        fill: true,
        tension: 0.4,
      }],
    },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1a1a2e',
          titleFont: { size: 12 },
          bodyFont: { size: 12 },
          callbacks: {
            label: c => ` ${c.parsed.y.toFixed(2)} ${cfg.label.match(/\(([^)]+)\)/)?.[1] || ''}`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { maxTicksLimit: 8, font: { size: 11 }, color: '#9ca3af' },
        },
        y: {
          grid: { color: '#f3f4f6', drawBorder: false },
          ticks: { font: { size: 11 }, color: '#9ca3af' },
        },
      },
    },
  });
}

/* ---- Metric toggle buttons ---- */
document.querySelectorAll('#metricBtns button').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#metricBtns button').forEach(b => {
      b.classList.remove('btn-success', 'active');
      b.classList.add('btn-outline-success');
    });
    btn.classList.remove('btn-outline-success');
    btn.classList.add('btn-success', 'active');
    loadChart(btn.dataset.metric);
  });
});

/* ---- Refresh sensor cards ---- */
async function refreshData() {
  try {
    const res = await fetch('/api/sensor/current');
    if (!res.ok) return;
    const data = await res.json();
    const r = data.readings;

    flash('val-moisture',    r.moisture.toFixed(1) + '%');
    flash('val-temperature', r.temperature.toFixed(1) + '°C');
    flash('val-ph',          r.ph.toFixed(2));
    flash('val-nitrogen',    Math.round(r.nitrogen));
    flash('val-phosphorus',  Math.round(r.phosphorus));
    flash('val-potassium',   Math.round(r.potassium));

    const ts = new Date().toLocaleTimeString();
    const el = document.getElementById('lastUpdated');
    if (el) el.innerHTML = `<i class="bi bi-circle-fill text-success me-1" style="font-size:.5rem;"></i>Updated ${ts}`;

    // Update ML prediction
    if (data.ml_prediction) updateMLPrediction(data.ml_prediction);

    // Re-render chart with fresh data
    loadChart(currentMetric);
  } catch (e) {
    console.error('Refresh failed:', e);
  }
}

function flash(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = value;
  el.style.opacity = '0.4';
  setTimeout(() => { el.style.transition = 'opacity .4s'; el.style.opacity = '1'; }, 50);
}

function updateMLPrediction(ml) {
  const cropEl = document.getElementById('ml-crop');
  const confEl = document.getElementById('ml-confidence');
  const top3El = document.getElementById('ml-top3');
  if (cropEl) cropEl.textContent = ml.crop || '—';
  if (confEl) confEl.textContent = ml.confidence ? ml.confidence + '%' : '—';
  if (top3El && ml.top3) {
    top3El.innerHTML = ml.top3.map(t =>
      `<span class="badge bg-light text-dark border small py-1 px-2">
        ${t.crop} <span class="text-muted">${t.probability}%</span>
      </span>`
    ).join('');
  }
}

/* ---- Auto-refresh every 30 seconds ---- */
setInterval(refreshData, 30000);

/* ---- Init ---- */
loadChart('moisture');
refreshData();
