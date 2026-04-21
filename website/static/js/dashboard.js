/* AgroBot — Dashboard JS */

const METRIC_CONFIG = {
  humidity:    { label: 'Humidity (%)',      color: '#0ea5e9', low: 40,   high: 80   },
  moisture:    { label: 'Moisture (%)',      color: '#0ea5e9', low: 40,   high: 80   },
  temperature: { label: 'Temperature (°C)', color: '#ef4444', low: 10,   high: 35   },
  ec:          { label: 'EC (µS/cm)',        color: '#f59e0b', low: 150,  high: 1200 },
  ph:          { label: 'pH',               color: '#8b5cf6', low: 5.5,  high: 7.5  },
  nitrogen:    { label: 'Nitrogen (mg/kg)', color: '#10b981', low: 30,   high: null },
};

let chart = null;
let currentMetric = 'humidity';
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
    if (r.humidity != null) flash('val-humidity', r.humidity.toFixed(1) + '%');
    if (r.ec      != null) flash('val-ec',       Math.round(r.ec));

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

/* ---- Rover path detection ---- */
const DIRECTION_ICONS = {
  LEFT:     { icon: '⬅', color: '#f59e0b' },
  RIGHT:    { icon: '➡', color: '#f59e0b' },
  STRAIGHT: { icon: '⬆', color: '#10b981' },
  STOP:     { icon: '🛑', color: '#ef4444' },
  UNKNOWN:  { icon: '⏸', color: '#9ca3af' },
};

function previewRoverImage(input) {
  const preview = document.getElementById('roverPreview');
  const placeholder = document.getElementById('roverPlaceholder');
  if (!input.files || !input.files[0]) return;
  const url = URL.createObjectURL(input.files[0]);
  preview.src = url;
  preview.classList.remove('d-none');
  placeholder.classList.add('d-none');
  // Reset result
  document.getElementById('directionIcon').textContent = '⏸';
  document.getElementById('directionLabel').textContent = '—';
  document.getElementById('pathCoverage').textContent = '—';
  document.getElementById('pathMask').classList.add('d-none');
  document.getElementById('maskPlaceholder').classList.remove('d-none');
}

async function detectPath() {
  const input = document.getElementById('roverImageInput');
  const errEl = document.getElementById('roverError');
  errEl.classList.add('d-none');

  if (!input.files || !input.files[0]) {
    errEl.textContent = 'Please select an image first.';
    errEl.classList.remove('d-none');
    return;
  }

  const btn = document.querySelector('[onclick="detectPath()"]');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Detecting…';

  try {
    const fd = new FormData();
    fd.append('image', input.files[0]);
    const res = await fetch('/api/rover/path', { method: 'POST', body: fd });
    const data = await res.json();

    if (data.error) {
      errEl.textContent = data.error;
      errEl.classList.remove('d-none');
      return;
    }

    const dir = data.direction || 'UNKNOWN';
    const cfg = DIRECTION_ICONS[dir] || DIRECTION_ICONS.UNKNOWN;

    document.getElementById('directionIcon').textContent = cfg.icon;
    const lbl = document.getElementById('directionLabel');
    lbl.textContent = dir;
    lbl.style.color = cfg.color;
    document.getElementById('pathCoverage').textContent = data.coverage + '%';

    if (data.mask_base64) {
      const mask = document.getElementById('pathMask');
      mask.src = 'data:image/png;base64,' + data.mask_base64;
      mask.classList.remove('d-none');
      document.getElementById('maskPlaceholder').classList.add('d-none');
    }
  } catch (e) {
    errEl.textContent = 'Detection failed: ' + e.message;
    errEl.classList.remove('d-none');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-play-fill me-1"></i>Detect Path';
  }
}

/* ---- Auto-refresh every 30 seconds ---- */
setInterval(refreshData, 30000);

/* ---- Init ---- */
loadChart('moisture');
refreshData();
