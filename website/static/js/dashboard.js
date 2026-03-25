/* AgroBot — Dashboard JS */

const METRIC_CONFIG = {
  moisture:    { label: 'Moisture (%)',     color: '#0d6efd', low: 40, high: 80 },
  temperature: { label: 'Temperature (°C)', color: '#dc3545', low: 10, high: 35 },
  ph:          { label: 'pH',               color: '#ffc107', low: 5.5, high: 7.5 },
  nitrogen:    { label: 'Nitrogen (mg/kg)', color: '#198754', low: 30, high: null },
};

let chart = null;
let currentMetric = 'moisture';
let historyData = [];

/* ---- Clock ---- */
function updateClock() {
  const el = document.getElementById('liveTime');
  if (el) el.textContent = new Date().toLocaleTimeString();
}
setInterval(updateClock, 1000);
updateClock();

/* ---- Fetch & render chart ---- */
async function loadChart(metric) {
  currentMetric = metric;
  try {
    const res = await fetch('/api/sensor/history?hours=24');
    historyData = await res.json();
    renderChart(metric);
  } catch (e) {
    console.error('Chart load failed:', e);
  }
}

function renderChart(metric) {
  const cfg = METRIC_CONFIG[metric];
  const labels = historyData.map(r => r.timestamp);
  const values = historyData.map(r => r[metric]);

  const ctx = document.getElementById('sensorChart');
  if (!ctx) return;

  if (chart) chart.destroy();

  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: cfg.label,
        data: values,
        borderColor: cfg.color,
        backgroundColor: cfg.color + '18',
        borderWidth: 2,
        pointRadius: 2,
        pointHoverRadius: 5,
        fill: true,
        tension: 0.4,
      }],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.parsed.y} ${cfg.label.match(/\(([^)]+)\)/)?.[1] || ''}`,
          },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 8, font: { size: 11 } } },
        y: { grid: { color: '#f0f0f0' }, ticks: { font: { size: 11 } } },
      },
    },
  });
}

/* ---- Toggle buttons ---- */
document.querySelectorAll('.chart-toggle').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.chart-toggle').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderChart(btn.dataset.metric);
  });
});

/* ---- Refresh sensor data ---- */
async function refreshData() {
  try {
    const res = await fetch('/api/sensor/current');
    const data = await res.json();
    const r = data.readings;

    setText('val-moisture',  r.moisture  + '%');
    setText('val-temp',      r.temperature + '°C');
    setText('val-ph',        r.ph);
    setText('val-n',         r.nitrogen);
    setText('val-p',         r.phosphorus);
    setText('val-k',         r.potassium);

    updateAlerts(data.alerts);
    updateRecs(data.recommendations);
    renderChart(currentMetric);
  } catch (e) {
    console.error('Refresh failed:', e);
  }
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) {
    el.classList.add('value-updated');
    el.textContent = value;
    setTimeout(() => el.classList.remove('value-updated'), 600);
  }
}

function updateAlerts(alerts) {
  const list = document.getElementById('alertList');
  if (!list || !alerts) return;
  list.innerHTML = alerts.map(a => `
    <li class="list-group-item d-flex align-items-start gap-2 py-3">
      <span class="badge bg-${a.level} mt-1 flex-shrink-0">
        <i class="bi bi-${a.level === 'danger' ? 'exclamation-triangle-fill' : a.level === 'warning' ? 'exclamation-circle-fill' : 'check-circle-fill'}"></i>
      </span>
      <div>
        <div class="small fw-semibold">${a.message}</div>
        <div class="text-muted" style="font-size:0.7rem;">${a.time}</div>
      </div>
    </li>`).join('');
}

function updateRecs(recs) {
  const el = document.getElementById('recCards');
  if (!el || !recs) return;
  el.innerHTML = recs.map(r => `
    <div class="col-md-6 col-lg-4">
      <div class="rec-item d-flex align-items-start gap-3 p-3 rounded-3 bg-${r.type}-subtle border border-${r.type}-subtle">
        <div class="rec-icon text-${r.type} flex-shrink-0">
          <i class="bi bi-${r.icon} fs-5"></i>
        </div>
        <div class="small">${r.message}</div>
      </div>
    </div>`).join('');
}

/* ---- Auto-refresh every 30 seconds ---- */
setInterval(refreshData, 30000);

/* ---- Init ---- */
loadChart('moisture');
