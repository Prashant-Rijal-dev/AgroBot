/* AgroBot — Field Analysis Map (Leaflet.js) */

const NEPAL_BOUNDS = [[26.0, 80.0], [30.5, 88.5]];
const NEPAL_CENTER = [28.3, 84.1];

const map = L.map('nepal-map', {
  center: NEPAL_CENTER,
  zoom: 7,
  maxBounds: [[24.0, 78.0], [32.5, 91.0]],
  maxBoundsViscosity: 0.8,
});

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  maxZoom: 18,
}).addTo(map);

L.rectangle(NEPAL_BOUNDS, {
  color: '#2d6a4f', weight: 2, fill: false, dashArray: '6,4', opacity: 0.6,
}).addTo(map);

let marker = null;

const greenIcon = L.divIcon({
  className: '',
  html: `<div style="
    width:28px;height:28px;border-radius:50% 50% 50% 0;
    background:#2d6a4f;border:3px solid #fff;
    box-shadow:0 2px 8px rgba(0,0,0,0.3);
    transform:rotate(-45deg);
  "></div>`,
  iconSize: [28, 28],
  iconAnchor: [14, 28],
});

map.on('click', function (e) {
  const { lat, lng } = e.latlng;
  if (marker) {
    marker.setLatLng([lat, lng]);
  } else {
    marker = L.marker([lat, lng], { icon: greenIcon }).addTo(map);
  }
  analyseField(lat, lng);
});

async function analyseField(lat, lon) {
  showPanel('loading');

  try {
    const res = await fetch('/api/field/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lat, lon }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `Server error ${res.status}`);
    }

    const data = await res.json();
    showResults(data);
  } catch (err) {
    showPanel('instruction');
    console.error('Field analysis error:', err);
    alert('Analysis failed: ' + err.message);
  }
}

// Show exactly one of: instruction | loading | results
function showPanel(which) {
  const panels = {
    instruction: document.getElementById('instructionPanel'),
    loading:     document.getElementById('loadingPanel'),
    results:     document.getElementById('resultsPanel'),
  };
  Object.entries(panels).forEach(([name, el]) => {
    if (!el) return;
    if (name === which) {
      el.classList.remove('d-none');
    } else {
      el.classList.add('d-none');
    }
  });
}

function showResults(d) {
  showPanel('results');

  setText('res-lat',  d.latitude  + '°N');
  setText('res-lon',  d.longitude + '°E');
  setText('res-soil', d.soil_type || 'Unknown');

  const elev = (d.elevation_min && d.elevation_max)
    ? `Elevation: ${d.elevation_min}m – ${d.elevation_max}m`
    : '';
  setText('res-elev', elev);

  // Maize bar
  const maizePct = d.maize_pct || 0;
  const maizeBar = document.getElementById('res-maize-bar');
  if (maizeBar) {
    maizeBar.style.width = maizePct + '%';
    maizeBar.className = 'progress-bar ' + suitabilityColor(d.maize_suitability);
  }
  setLabel('res-maize-label', d.maize_label || '—', d.maize_suitability);
  setText('res-maize-score', d.maize_suitability ? `Score: ${d.maize_suitability}/127` : '');

  // Tomato bar
  const tomatoPct = d.tomato_pct || 0;
  const tomatoBar = document.getElementById('res-tomato-bar');
  if (tomatoBar) {
    tomatoBar.style.width = tomatoPct + '%';
    tomatoBar.className = 'progress-bar ' + suitabilityColor(d.tomato_suitability);
  }
  setLabel('res-tomato-label', d.tomato_label || '—', d.tomato_suitability);
  setText('res-tomato-score', d.tomato_suitability ? `Score: ${d.tomato_suitability}/127` : '');

  setText('res-crop', d.recommended_crop || '—');
  setText('res-text', d.recommendation_text || '—');

  if (marker) {
    marker.bindPopup(`
      <strong>${d.soil_type || 'Unknown soil'}</strong><br>
      Recommended: <b>${d.recommended_crop || '—'}</b><br>
      <small>Maize: ${d.maize_suitability ?? '—'} | Tomato: ${d.tomato_suitability ?? '—'}</small>
    `).openPopup();
  }
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function setLabel(id, text, score) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.className = 'badge ' + badgeClass(score);
}

function suitabilityColor(score) {
  if (!score) return 'bg-secondary';
  if (score >= 100) return 'bg-success';
  if (score >= 70)  return 'bg-primary';
  if (score >= 40)  return 'bg-warning';
  return 'bg-danger';
}

function badgeClass(score) {
  if (!score) return 'bg-secondary';
  if (score >= 100) return 'bg-success';
  if (score >= 70)  return 'bg-primary';
  if (score >= 40)  return 'bg-warning';
  return 'bg-danger';
}

// History items — click to re-analyse
document.querySelectorAll('.history-item').forEach(item => {
  item.addEventListener('click', () => {
    const lat = parseFloat(item.dataset.lat);
    const lon = parseFloat(item.dataset.lon);
    map.setView([lat, lon], 10);
    if (marker) {
      marker.setLatLng([lat, lon]);
    } else {
      marker = L.marker([lat, lon], { icon: greenIcon }).addTo(map);
    }
    analyseField(lat, lon);
  });
});
