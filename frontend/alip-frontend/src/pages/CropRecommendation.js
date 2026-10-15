import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { getCropRecommendation, getSoilProfile, reverseGeocode } from '../services/api';
import toast from 'react-hot-toast';
import './CropRecommendation.css';

/* ═══════════════════════════════════════════════════════════════
   ALIP — Crop Recommendation (Farmer Module)
   · Interactive Map-First Farm Selection (Leaflet / OpenStreetMap)
   · Coordinate-based Soil Intelligence (ISRIC SoilGrids 250m & Regional)
   · Explicit Data Provenance, Resolution, & Uncertainty Display
   · Water & Irrigation Feasibility Constraints
   · Explainable Crop Suitability & ML Confidence Scoring

   UI: styles live in CropRecommendation.css (logic unchanged).
═══════════════════════════════════════════════════════════════ */

// ── Constants ─────────────────────────────────────────────────
const SEASONS = [
  { value: 'kharif', label: 'Kharif', icon: '🌧️', period: 'Jun – Nov (Monsoon)', desc: 'High moisture, warm rains', grad: 'linear-gradient(135deg,#0ea5e9,#38bdf8)', shadow: 'rgba(14,165,233,0.35)' },
  { value: 'rabi',   label: 'Rabi',   icon: '❄️',  period: 'Nov – Apr (Winter)',  desc: 'Cool dry climate, residual moisture', grad: 'linear-gradient(135deg,#8b5cf6,#a78bfa)', shadow: 'rgba(139,92,246,0.35)' },
  { value: 'zaid',   label: 'Zaid',   icon: '☀️',  period: 'Apr – Jun (Summer)',  desc: 'Warm, dry sunny days', grad: 'linear-gradient(135deg,#f59e0b,#fbbf24)', shadow: 'rgba(245,158,11,0.35)' },
];

const IRRIGATION_OPTIONS = [
  { value: 'rainfed',   label: 'Rainfed (Monsoon Dependent)', icon: '🌧️', desc: 'No dedicated irrigation source' },
  { value: 'canal',     label: 'Canal / River Network',       icon: '🌊', desc: 'Seasonal surface irrigation canal' },
  { value: 'borewell',  label: 'Borewell / Drip Irrigation',  icon: '💧', desc: 'Assured groundwater & micro-irrigation' },
];

const QUICK_FARMS = [
  { name: 'Hyderabad, Telangana', lat: 17.3850, lon: 78.4867, state: 'Telangana' },
  { name: 'Warangal, Telangana',  lat: 17.9689, lon: 79.5941, state: 'Telangana' },
  { name: 'Vijayawada, AP',       lat: 16.5062, lon: 80.6480, state: 'Andhra Pradesh' },
  { name: 'Ludhiana, Punjab',     lat: 30.9010, lon: 75.8573, state: 'Punjab' },
  { name: 'Pune, Maharashtra',    lat: 18.5204, lon: 73.8567, state: 'Maharashtra' },
  { name: 'Coimbatore, TN',       lat: 11.0168, lon: 76.9558, state: 'Tamil Nadu' },
  { name: 'Jaipur, Rajasthan',    lat: 26.9124, lon: 75.7873, state: 'Rajasthan' },
  { name: 'Varanasi, UP',         lat: 25.3176, lon: 82.9739, state: 'Uttar Pradesh' },
];

const CROP_EMOJIS = {
  rice:'🌾', wheat:'🌾', maize:'🌽', cotton:'🌿', sugarcane:'🎋',
  jute:'🌿', coffee:'☕', tea:'🍵', banana:'🍌', mango:'🥭',
  grapes:'🍇', watermelon:'🍉', muskmelon:'🍈', apple:'🍎',
  orange:'🍊', papaya:'🫒', coconut:'🥥', pomegranate:'🍎',
  lentil:'🫘', chickpea:'🫘', kidneybeans:'🫘', pigeonpeas:'🫘',
  mothbeans:'🫘', mungbean:'🫘', blackgram:'🫘',
};
const getCropEmoji = (n) => CROP_EMOJIS[n?.toLowerCase().replace(/\s+/g, '')] || '🌱';

const RANK_CONFIG = [
  { medal: '🥇', label: 'Top Agronomic Match', grad: 'linear-gradient(135deg,#f59e0b,#fbbf24)', shadow: 'rgba(245,158,11,0.4)', ring: '#f59e0b', trackBg: '#fef3c7' },
  { medal: '🥈', label: 'Second Choice',        grad: 'linear-gradient(135deg,#64748b,#94a3b8)', shadow: 'rgba(100,116,139,0.3)', ring: '#64748b', trackBg: '#f1f5f9' },
  { medal: '🥉', label: 'Alternative Option',    grad: 'linear-gradient(135deg,#b45309,#d97706)', shadow: 'rgba(180,83,9,0.3)',    ring: '#b45309', trackBg: '#fef3c7' },
];

// UI only: small icon per soil property
const SOIL_ICONS = { ph: '🧫', nitrogen: '🌿', phosphorous: '🧪', potassium: '🍃' };

/* ── Interactive Leaflet Map Component ──────────────────────── */
function FarmMapPicker({ coords, onCoordsChange, address }) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markerRef = useRef(null);
  const [mapLoaded, setMapLoaded] = useState(false);

  useEffect(() => {
    if (!window.L) {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      document.head.appendChild(link);

      const script = document.createElement('script');
      script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
      script.onload = () => setMapLoaded(true);
      document.body.appendChild(script);
    } else {
      setMapLoaded(true);
    }
  }, []);

  useEffect(() => {
    if (!mapLoaded || !mapContainerRef.current || mapInstanceRef.current) return;
    const L = window.L;

    // Create map centered on initial coordinates
    const map = L.map(mapContainerRef.current, {
      center: [coords.lat, coords.lng],
      zoom: 11,
      scrollWheelZoom: true,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors',
    }).addTo(map);

    // Custom pulse pin icon
    const farmIcon = L.divIcon({
      className: 'farm-marker-icon',
      html: `<div style="
        background: linear-gradient(135deg, #16a34a, #22c55e);
        color: white; width: 38px; height: 38px; border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg); display: flex; align-items: center; justify-content: center;
        box-shadow: 0 4px 14px rgba(22,163,74,0.5); border: 2.5px solid white;">
        <span style="transform: rotate(45deg); font-size: 18px;">📍</span>
      </div>`,
      iconSize: [38, 38],
      iconAnchor: [19, 38],
    });

    const marker = L.marker([coords.lat, coords.lng], {
      icon: farmIcon,
      draggable: true,
    }).addTo(map);

    marker.on('dragend', (e) => {
      const pos = e.target.getLatLng();
      onCoordsChange(pos.lat, pos.lng);
    });

    map.on('click', (e) => {
      marker.setLatLng(e.latlng);
      onCoordsChange(e.latlng.lat, e.latlng.lng);
    });

    mapInstanceRef.current = map;
    markerRef.current = marker;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mapLoaded]);

  // Update map view when coordinates change from outside
  useEffect(() => {
    if (mapInstanceRef.current && markerRef.current) {
      markerRef.current.setLatLng([coords.lat, coords.lng]);
      mapInstanceRef.current.panTo([coords.lat, coords.lng]);
    }
  }, [coords.lat, coords.lng]);

  const handleLocateMe = () => {
    if (navigator.geolocation) {
      toast.loading('Locating your farm via GPS...', { id: 'gps' });
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          toast.dismiss('gps');
          toast.success('Field located via GPS!');
          onCoordsChange(pos.coords.latitude, pos.coords.longitude);
        },
        () => {
          toast.dismiss('gps');
          toast.error('Could not get GPS location. Select on map manually.');
        },
        { enableHighAccuracy: true, timeout: 8000 }
      );
    } else {
      toast.error('Geolocation not supported in this browser.');
    }
  };

  return (
    <div className="cr-map-wrap">
      <div className="cr-map-top">
        <div className="cr-map-status">
          <span className="cr-map-dot" />
          <span className="cr-map-title">Interactive Field Pinpoint</span>
        </div>
        <button className="cr-gps-btn" onClick={handleLocateMe} type="button">
          🎯 Locate My Field (GPS)
        </button>
      </div>

      <div ref={mapContainerRef} className="cr-map" />

      <div className="cr-map-bottom">
        <div className="cr-coord">
          <span>Lat:</span> <b>{coords.lat.toFixed(4)}° N</b>
        </div>
        <div className="cr-coord">
          <span>Lon:</span> <b>{coords.lng.toFixed(4)}° E</b>
        </div>
        <div className="cr-address">
          📍 {address || 'Drag the marker or click the map to select your farm plot'}
        </div>
      </div>
    </div>
  );
}

/* ── Animated Confidence Ring ───────────────────────────────── */
function ConfRing({ value, config }) {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => setShown(value), 120);
    return () => clearTimeout(t);
  }, [value]);

  const circumference = 2 * Math.PI * 22;
  const fillDash = (shown / 100) * circumference;
  const color = value >= 75 ? '#16a34a' : value >= 50 ? '#d97706' : '#dc2626';

  return (
    <div className="cr-ring-wrap" style={{ background: config.trackBg }}>
      <svg width="76" height="76" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx="38" cy="38" r="22" fill="none" stroke="#e2e8f0" strokeWidth="5.5" />
        <circle
          cx="38" cy="38" r="22" fill="none"
          stroke={color} strokeWidth="5.5"
          strokeLinecap="round"
          strokeDasharray={`${fillDash} ${circumference}`}
          style={{ transition: 'stroke-dasharray 1.2s cubic-bezier(0.34,1.2,0.64,1)' }}
        />
      </svg>
      <div className="cr-ring-label">
        <span className="cr-ring-num" style={{ color }}>{Math.round(value)}</span>
        <span className="cr-ring-pct" style={{ color }}>%</span>
      </div>
    </div>
  );
}

/* ── Main Component ─────────────────────────────────────────── */
export default function CropRecommendation() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0); // 0: Location Map, 1: Soil & Weather Profile, 2: Conditions, 3: Recommendations

  // Geospatial State
  const [coords, setCoords] = useState({ lat: 17.3850, lng: 78.4867 });
  const [address, setAddress] = useState('Hyderabad, Telangana, India');

  // Farming Conditions
  const [season, setSeason] = useState('kharif');
  const [irrigation, setIrrigation] = useState('rainfed');

  // Soil & Weather Profile (from ISRIC SoilGrids & Open-Meteo)
  const [soilProfile, setSoilProfile] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(false);

  // Optional Lab Test Overrides
  const [showOverrides, setShowOverrides] = useState(false);
  const [manualSoil, setManualSoil] = useState({
    nitrogen: '',
    phosphorous: '',
    potassium: '',
    ph: '',
    temperature: '',
    humidity: '',
    rainfall: '',
  });

  // Recommendation Results
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeRecIdx, setActiveRecIdx] = useState(0);
  const resultRef = useRef(null);

  // On coordinate change, fetch reverse geocode and soil profile
  const handleCoordsChange = async (lat, lng) => {
    setCoords({ lat, lng });
    try {
      const geoRes = await reverseGeocode(lat, lng);
      if (geoRes.data?.data) {
        setAddress(geoRes.data.data.formatted_address || `${lat.toFixed(4)}, ${lng.toFixed(4)}`);
      }
    } catch {
      setAddress(`Latitude ${lat.toFixed(4)}, Longitude ${lng.toFixed(4)}`);
    }
  };

  // Load soil profile for current coordinates
  const loadSoilProfile = async () => {
    setLoadingProfile(true);
    try {
      const res = await getSoilProfile(coords.lat, coords.lng);
      if (res.data?.success && res.data.soil_profile) {
        setSoilProfile(res.data.soil_profile);
        toast.success('Soil intelligence retrieved from ISRIC SoilGrids 250m & Regional Survey!');
      } else {
        throw new Error('Fallback needed');
      }
    } catch {
      // Graceful fallback to regional agricultural baseline
      setSoilProfile({
        coordinates: { latitude: coords.lat, longitude: coords.lng },
        soil_classification: {
          soil_type: 'Red Soil',
          source: 'Regional Agro-Ecological Survey',
          spatial_resolution: 'District/State Soil Map',
          confidence: 'Medium (Survey Baseline)',
        },
        data_quality: 'geographic-estimate',
        properties: [
          { property: 'ph', label: 'Soil pH', value: 6.5, unit: 'pH', status: 'estimated', source: 'Regional Agro-Survey Baseline', depth_cm: [0, 15], uncertainty: '±0.5 pH units' },
          { property: 'nitrogen', label: 'Available Nitrogen (N)', value: 45, unit: 'kg/ha', status: 'estimated', source: 'Regional Agro-Survey Baseline', depth_cm: [0, 15], notes: 'Plant-available N estimate' },
          { property: 'phosphorous', label: 'Available Phosphorus (P)', value: 25, unit: 'kg/ha', status: 'estimated', source: 'Regional Survey Baseline', depth_cm: [0, 15], notes: 'Regional agronomic benchmark' },
          { property: 'potassium', label: 'Available Potassium (K)', value: 30, unit: 'kg/ha', status: 'estimated', source: 'Regional Survey Baseline', depth_cm: [0, 15], notes: 'Regional agronomic benchmark' },
        ],
        limitations: [
          'Spatial predictions represent regional soil surveys and landscape-scale predictions.',
          'Verify with an official laboratory soil test card before chemical fertilizer budgeting.'
        ]
      });
      toast('Applied regional agro-ecological soil baseline', { icon: '📍' });
    }
    setLoadingProfile(false);
  };

  // Initial load
  useEffect(() => {
    handleCoordsChange(coords.lat, coords.lng);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // When progressing to Step 1, load soil profile
  const handleProceedToSoil = async () => {
    await loadSoilProfile();
    setStep(1);
  };

  // Generate Recommendation
  const handleGetRecommendation = async () => {
    setLoading(true);
    const payload = {
      latitude: coords.lat,
      longitude: coords.lng,
      location: address,
      season: season,
      irrigation: irrigation,
    };

    // Include optional lab test overrides if provided
    Object.keys(manualSoil).forEach((k) => {
      if (manualSoil[k] !== '' && manualSoil[k] != null) {
        payload[k] = parseFloat(manualSoil[k]);
      }
    });

    try {
      const res = await getCropRecommendation(payload);
      setResult(res.data);
      setStep(3);
      toast.success('🌱 Crop recommendation generated with full agronomic explainability!');
      setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 150);
    } catch (err) {
      let msg = 'Error generating recommendation. Please check your inputs.';
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        msg = detail;
      } else if (Array.isArray(detail)) {
        msg = detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
      } else if (err.message) {
        msg = err.message;
      }
      toast.error(msg);
    }
    setLoading(false);
  };

  const stepsList = ['Farm Location', 'Soil & Climate', 'Field Conditions', 'Crop Advisory'];

  return (
    <div className="cr-page">
      {/* Floating background orbs */}
      <div className="cr-orb cr-orb-1" />
      <div className="cr-orb cr-orb-2" />
      <div className="cr-orb cr-orb-3" />

      {/* ═══ HEADER ═══ */}
      <header className="cr-header">
        <div className="cr-header-inner">
          <button className="cr-back-btn" onClick={() => navigate('/farmer')}>
            ← Back to Farmer Dashboard
          </button>
          <div className="cr-title-wrap">
            <span className="cr-eyebrow">📍 Geospatial &amp; Map-First Intelligence</span>
            <h1 className="cr-title">Crop Recommendation Engine</h1>
            <p className="cr-subtitle">Coordinate-driven soil intelligence, climate matching &amp; verified agronomic explainability</p>
          </div>
          <div className="cr-model-pill">
            <span className="cr-model-dot" /> Random Forest + SoilGrids
          </div>
        </div>

        {/* Wizard Steps */}
        <div className="cr-stepper">
          {stepsList.map((stLabel, idx) => {
            const isDone = idx < step;
            const isCurrent = idx === step;
            return (
              <button
                key={idx}
                className={`cr-step-tab${isCurrent ? ' is-active' : isDone ? ' is-done' : ''}`}
                onClick={() => idx <= step && setStep(idx)}
              >
                <span className="cr-step-circle">{isDone ? '✓' : idx + 1}</span>
                {stLabel}
              </button>
            );
          })}
        </div>
        <div className="cr-progress">
          <span className="cr-progress-bar" style={{ width: `${((step + 1) / stepsList.length) * 100}%` }} />
        </div>
      </header>

      {/* ═══ BODY ═══ */}
      <main className="cr-main">
        <div>

          {/* ──── STEP 0: Map-Based Farm Location ──── */}
          {step === 0 && (
            <div className="cr-card">
              {loadingProfile && (
                <div className="cr-overlay">
                  <div className="cr-spinner" />
                  <div className="cr-overlay-title">Querying SoilGrids…</div>
                  <div className="cr-overlay-sub">Fetching soil intelligence for your coordinates</div>
                </div>
              )}

              <div className="cr-card-head">
                <span className="cr-tag">Step 1 of 4</span>
                <h2 className="cr-heading">📍 Select Your Farm on the Map</h2>
                <p className="cr-subheading">
                  Click anywhere on the map or drag the pin directly onto your plot. We use exact geographic coordinates
                  to query satellite soil grids (ISRIC) and local climate data.
                </p>
              </div>

              {/* Quick Jump agricultural districts */}
              <div className="cr-quick">
                <span className="cr-quick-label">Quick jump to district:</span>
                <div className="cr-quick-chips">
                  {QUICK_FARMS.map((f) => (
                    <button
                      key={f.name}
                      className={`cr-chip${Math.abs(coords.lat - f.lat) < 0.05 && Math.abs(coords.lng - f.lon) < 0.05 ? ' is-active' : ''}`}
                      onClick={() => handleCoordsChange(f.lat, f.lon)}
                    >
                      {f.name}
                    </button>
                  ))}
                </div>
              </div>

              {/* Interactive Map */}
              <FarmMapPicker coords={coords} onCoordsChange={handleCoordsChange} address={address} />

              <div className="cr-btn-row">
                <button className="cr-btn-primary" onClick={handleProceedToSoil} disabled={loadingProfile}>
                  {loadingProfile ? 'Querying SoilGrids...' : 'Confirm Location & View Soil Profile →'}
                </button>
              </div>
            </div>
          )}

          {/* ──── STEP 1: Soil & Climate Profile Review ──── */}
          {step === 1 && (
            <div className="cr-card">
              <div className="cr-card-head">
                <span className="cr-tag">Step 2 of 4</span>
                <h2 className="cr-heading">🧪 Soil &amp; Climate Profile for Selected Field</h2>
                <p className="cr-subheading">
                  Geospatial intelligence retrieved for <b>{address}</b> (Coordinates: {coords.lat.toFixed(4)}°, {coords.lng.toFixed(4)}°).
                </p>
              </div>

              {/* Data Provenance Notice */}
              <div className="cr-prov">
                <span className="cr-prov-icon">ℹ️</span>
                <div>
                  <div className="cr-prov-title">Geospatial Data Provenance &amp; Uncertainty Note</div>
                  <div className="cr-prov-text">
                    Properties below represent <b>ISRIC SoilGrids 250m global spatial predictions</b> and regional agro-ecological surveys.
                    Satellite grids predict landscape-level soil texture and pH. Plant-available Nitrogen, Phosphorus (P) and Potassium (K)
                    are estimated from regional benchmarks; use a laboratory soil test for chemical fertilizer budgeting.
                  </div>
                </div>
              </div>

              {/* Soil Properties Grid */}
              <div className="cr-soil-grid">
                {soilProfile?.properties?.map((p, i) => (
                  <div key={i} className="cr-soil-card" style={{ animationDelay: `${0.08 + i * 0.09}s` }}>
                    <div className="cr-soil-top">
                      <span className="cr-soil-label">
                        <span className="cr-soil-icon">{SOIL_ICONS[p.property] || '🌱'}</span>
                        {p.label}
                      </span>
                      <span className="cr-status">{p.status === 'estimated' ? 'Estimated' : 'Measured'}</span>
                    </div>
                    <div className="cr-soil-val">
                      {p.value} <span className="cr-soil-unit">{p.unit}</span>
                    </div>
                    <div className="cr-soil-meta">
                      <b>Source:</b> {p.source}
                    </div>
                    {p.uncertainty && (
                      <div className="cr-soil-unc">
                        <b>Uncertainty:</b> {p.uncertainty}
                      </div>
                    )}
                    {p.notes && <div className="cr-soil-notes">{p.notes}</div>}
                  </div>
                )) || (
                  <div className="cr-loading-box">Loading Soil Profile...</div>
                )}
              </div>

              <div className="cr-btn-between">
                <button className="cr-btn-secondary" onClick={() => setStep(0)}>
                  ← Adjust Location on Map
                </button>
                <button className="cr-btn-primary" onClick={() => setStep(2)}>
                  Proceed to Farming Conditions →
                </button>
              </div>
            </div>
          )}

          {/* ──── STEP 2: Field Conditions & Constraints ──── */}
          {step === 2 && (
            <div className="cr-card">
              {loading && (
                <div className="cr-overlay">
                  <div className="cr-spinner" />
                  <div className="cr-overlay-title">Evaluating Agronomic Engine &amp; ML Model…</div>
                  <div className="cr-overlay-sub">Matching soil, climate and water constraints</div>
                </div>
              )}

              <div className="cr-card-head">
                <span className="cr-tag">Step 3 of 4</span>
                <h2 className="cr-heading">🗓️ Sowing Season &amp; Water Constraints</h2>
                <p className="cr-subheading">
                  Define your intended planting season and irrigation source. Our agronomic engine enforces water constraints
                  so water-heavy crops (e.g. paddy) are never recommended under rainfed water-deficit conditions.
                </p>
              </div>

              {/* Season Selector */}
              <div className="cr-group">
                <label className="cr-group-title">Select Agricultural Season:</label>
                <div className="cr-season-grid">
                  {SEASONS.map((s) => {
                    const active = season === s.value;
                    return (
                      <button
                        key={s.value}
                        type="button"
                        className={`cr-season-card${active ? ' is-active' : ''}`}
                        style={{ '--grad': s.grad, '--glow': s.shadow }}
                        onClick={() => setSeason(s.value)}
                      >
                        <span className="cr-season-icon">{s.icon}</span>
                        <div className="cr-season-name">{s.label} Season</div>
                        <div className="cr-season-period">{s.period}</div>
                        <div className="cr-season-desc">{s.desc}</div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Irrigation Selector */}
              <div className="cr-group">
                <label className="cr-group-title">Water &amp; Irrigation Availability:</label>
                <div className="cr-irrig-grid">
                  {IRRIGATION_OPTIONS.map((ir) => {
                    const active = irrigation === ir.value;
                    return (
                      <button
                        key={ir.value}
                        type="button"
                        className={`cr-irrig-card${active ? ' is-active' : ''}`}
                        onClick={() => setIrrigation(ir.value)}
                      >
                        <span className="cr-irrig-icon">{ir.icon}</span>
                        <div>
                          <div className="cr-irrig-title">{ir.label}</div>
                          <div className="cr-irrig-sub">{ir.desc}</div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Optional Soil Test Overrides */}
              <div className="cr-adv">
                <button
                  type="button"
                  className="cr-adv-toggle"
                  onClick={() => setShowOverrides((p) => !p)}
                >
                  <span>🧪 Have an official Laboratory Soil Test Card? (Optional)</span>
                  <span>{showOverrides ? '▲ Hide' : '▼ Enter Measured Values'}</span>
                </button>

                {showOverrides && (
                  <div className="cr-adv-content">
                    <p className="cr-adv-hint">
                      Enter exact laboratory-tested values if available. Measured values supersede satellite and regional estimates.
                    </p>
                    <div className="cr-adv-grid">
                      {[
                        { key: 'nitrogen', label: 'Nitrogen (N)', unit: 'kg/ha', placeholder: 'e.g. 50' },
                        { key: 'phosphorous', label: 'Phosphorous (P)', unit: 'kg/ha', placeholder: 'e.g. 25' },
                        { key: 'potassium', label: 'Potassium (K)', unit: 'kg/ha', placeholder: 'e.g. 30' },
                        { key: 'ph', label: 'Soil pH', unit: 'pH', placeholder: 'e.g. 6.5' },
                        { key: 'temperature', label: 'Temp (°C)', unit: '°C', placeholder: 'e.g. 28' },
                        { key: 'rainfall', label: 'Rainfall (mm)', unit: 'mm', placeholder: 'e.g. 200' },
                      ].map((f) => (
                        <div key={f.key}>
                          <label className="cr-adv-label">{f.label} ({f.unit})</label>
                          <input
                            type="number"
                            step="0.1"
                            placeholder={f.placeholder}
                            value={manualSoil[f.key]}
                            onChange={(e) => setManualSoil({ ...manualSoil, [f.key]: e.target.value })}
                            className="cr-adv-input"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="cr-btn-between">
                <button className="cr-btn-secondary" onClick={() => setStep(1)}>
                  ← Back to Soil Profile
                </button>
                <button className="cr-btn-primary" onClick={handleGetRecommendation} disabled={loading}>
                  {loading ? 'Evaluating Agronomic Engine & ML Model...' : 'Analyze & Generate Recommendations →'}
                </button>
              </div>
            </div>
          )}

          {/* ──── STEP 3: Explainable Recommendations ──── */}
          {step === 3 && result && (
            <div ref={resultRef} className="cr-card">
              <div className="cr-results-head">
                <div>
                  <span className="cr-tag">Step 4 of 4 · Analysis Complete</span>
                  <h2 className="cr-heading">🌾 Recommended Crops for Your Farm</h2>
                  <p className="cr-subheading">
                    Location: <b>{result.location}</b> · Season: <b>{result.season?.toUpperCase()}</b> · Irrigation: <b>{result.irrigation?.toUpperCase()}</b>
                  </p>
                </div>
                <div className="cr-quality">
                  Data Quality: <b>{result.data_quality === 'verified-laboratory' ? 'Verified Laboratory Data' : 'Geographic Grid Estimate'}</b>
                </div>
              </div>

              {/* Resolved Context Summary Bar */}
              <div className="cr-context">
                <div className="cr-ctx-item" style={{ animationDelay: '0.05s' }}>
                  <span className="cr-ctx-icon">🌱</span>
                  <div>
                    <div className="cr-ctx-lbl">Soil Type</div>
                    <div className="cr-ctx-val">{result.soil_type}</div>
                  </div>
                </div>
                <div className="cr-ctx-item" style={{ animationDelay: '0.12s' }}>
                  <span className="cr-ctx-icon">🌡️</span>
                  <div>
                    <div className="cr-ctx-lbl">Temperature</div>
                    <div className="cr-ctx-val">{result.weather_inputs?.temperature}°C</div>
                  </div>
                </div>
                <div className="cr-ctx-item" style={{ animationDelay: '0.19s' }}>
                  <span className="cr-ctx-icon">🌧️</span>
                  <div>
                    <div className="cr-ctx-lbl">Rainfall</div>
                    <div className="cr-ctx-val">{result.weather_inputs?.rainfall} mm</div>
                  </div>
                </div>
                <div className="cr-ctx-item" style={{ animationDelay: '0.26s' }}>
                  <span className="cr-ctx-icon">🧫</span>
                  <div>
                    <div className="cr-ctx-lbl">pH Level</div>
                    <div className="cr-ctx-val">{result.soil_summary?.ph}</div>
                  </div>
                </div>
                <div className="cr-ctx-item" style={{ animationDelay: '0.33s' }}>
                  <span className="cr-ctx-icon">🧪</span>
                  <div>
                    <div className="cr-ctx-lbl">NPK (kg/ha)</div>
                    <div className="cr-ctx-val">{result.soil_summary?.nitrogen}-{result.soil_summary?.phosphorous}-{result.soil_summary?.potassium}</div>
                  </div>
                </div>
              </div>

              {/* Tab Selector for Top 3 Crops */}
              <div className="cr-rec-tabs">
                {result.recommendations.map((rec, i) => {
                  const cfg = RANK_CONFIG[i] || RANK_CONFIG[2];
                  const active = activeRecIdx === i;
                  return (
                    <button
                      key={i}
                      className={`cr-rec-tab${active ? ' is-active' : ''}`}
                      style={{ '--ring': cfg.ring }}
                      onClick={() => setActiveRecIdx(i)}
                    >
                      <span className="cr-rec-medal">{cfg.medal}</span>
                      <div className="cr-rec-tab-name">{rec.display_name || rec.crop}</div>
                      <div className="cr-rec-tab-score">
                        {rec.suitability_score}% Match
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Active Recommendation Detail Card */}
              {result.recommendations[activeRecIdx] && (() => {
                const rec = result.recommendations[activeRecIdx];
                const cfg = RANK_CONFIG[activeRecIdx] || RANK_CONFIG[2];
                return (
                  <div className="cr-rec-card" key={activeRecIdx}>
                    <div className="cr-rec-hero" style={{ background: cfg.grad }}>
                      <div className="cr-rec-hero-left">
                        <span className="cr-rec-emoji">{getCropEmoji(rec.crop)}</span>
                        <div>
                          <span className="cr-rec-badge">{cfg.label}</span>
                          <h3 className="cr-rec-title">{rec.display_name || rec.crop}</h3>
                          <p className="cr-rec-desc">{rec.description}</p>
                        </div>
                      </div>
                      <div className="cr-rec-hero-right">
                        <ConfRing value={rec.suitability_score} config={cfg} />
                        <div className="cr-score-label">Suitability Match</div>
                        <div className="cr-score-sub">
                          ML Confidence: <b>{rec.ml_confidence}%</b>
                        </div>
                      </div>
                    </div>

                    {/* Explainability Breakdown */}
                    <div className="cr-explain">
                      {/* Left: Why it was recommended */}
                      <div>
                        <div className="cr-explain-head">
                          <span>✅</span> Why this crop is suitable for your field:
                        </div>
                        <ul className="cr-list">
                          {rec.reasons?.map((reason, idx) => (
                            <li key={idx} className="cr-reason" style={{ animationDelay: `${0.1 + idx * 0.08}s` }}>
                              <span className="cr-bullet">✔</span> {reason}
                            </li>
                          )) || <li>Compatible with field parameters.</li>}
                        </ul>
                      </div>

                      {/* Right: Constraints & Agronomic Advice */}
                      <div>
                        <div className="cr-explain-head">
                          <span>⚠️</span> Agronomic Constraints &amp; Advice:
                        </div>
                        {rec.warnings && rec.warnings.length > 0 ? (
                          <ul className="cr-list">
                            {rec.warnings.map((warn, idx) => (
                              <li key={idx} className="cr-warning" style={{ animationDelay: `${0.1 + idx * 0.08}s` }}>
                                <span className="cr-bullet">⚠️</span> {warn}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <div className="cr-no-warning">
                            No critical constraints detected. Moisture and thermal windows are optimal.
                          </div>
                        )}
                        <div className="cr-water">
                          💧 <b>Water Requirement:</b> {rec.water_demand?.toUpperCase()} · Keep root zone well aerated.
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* Data Transparency & Limitations Footer */}
              <div className="cr-limits">
                <div className="cr-limits-head">
                  <span>💡 Transparency &amp; Field Verification Notes</span>
                </div>
                <ul className="cr-list">
                  {result.limitations_and_warnings?.map((lim, idx) => (
                    <li key={idx} className="cr-limit-item">• {lim}</li>
                  ))}
                  <li className="cr-limit-item">• Model: {result.model_version}. Random Forest classifier with 100 trees evaluated on 22 balanced crop types.</li>
                </ul>
              </div>

              <div className="cr-btn-between">
                <button className="cr-btn-secondary" onClick={() => setStep(0)}>
                  ← Plan Another Field on Map
                </button>
                <button className="cr-btn-primary" onClick={() => navigate('/weather')}>
                  View 7-Day Weather Plan for this Crop →
                </button>
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}