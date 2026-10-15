import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { getWeatherAdvisory } from '../services/api';
import toast from 'react-hot-toast';
import './WeatherAdvisory.css';

const SEVERITY = {
  high:   { color: '#e5483b', label: 'High' },
  medium: { color: '#f2a431', label: 'Medium' },
  low:    { color: '#2f9e5e', label: 'Low' }
};

// UI only: icon shown beside each advisory
const SEVERITY_ICON = { high: '🚨', medium: '⚠️', low: '🌱' };

const COMMON_DISEASES = [
  "Tomato - Early Blight",
  "Tomato - Late Blight",
  "Potato - Early Blight",
  "Potato - Late Blight",
  "Corn - Common Rust",
  "Apple - Apple Scab",
  "Rice - Blast Disease",
  "Cotton - Bacterial Blight",
  "General Crop Protection"
];

/* ---------- small hooks ---------- */
function useCountUp(target, ms = 1300) {
  const [v, setV] = useState(0);
  useEffect(() => {
    const end = Number(target) || 0;
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { setV(end); return; }
    let raf, start;
    const tick = (t) => {
      start = start ?? t;
      const p = Math.min((t - start) / ms, 1);
      setV(end * (1 - Math.pow(1 - p, 3)));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, ms]);
  return v;
}

/* ---------- page ---------- */
export default function WeatherAdvisory() {
  const navigate = useNavigate();
  const routeLocation = useLocation();

  const [location, setLocation] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);

  // Recent Disease Detection Context
  const [recentDisease, setRecentDisease] = useState(null);
  const [selectedDisease, setSelectedDisease] = useState('');
  const [selectedSeverity, setSelectedSeverity] = useState('high');
  const [activeDayTab, setActiveDayTab] = useState(1);

  // Load recent disease from state or localStorage
  useEffect(() => {
    let diseaseCtx = routeLocation.state?.diseaseContext;
    let sevCtx = routeLocation.state?.severity;

    if (!diseaseCtx) {
      try {
        const stored = localStorage.getItem('recent_disease_detection');
        if (stored) {
          const parsed = JSON.parse(stored);
          diseaseCtx = parsed.full_disease || parsed.disease;
          sevCtx = parsed.severity || 'medium';
          setRecentDisease(parsed);
        }
      } catch (err) {
        console.warn('Failed to read cached disease:', err);
      }
    }

    if (diseaseCtx) {
      setSelectedDisease(diseaseCtx);
      if (sevCtx) setSelectedSeverity(sevCtx);
    }
  }, [routeLocation.state]);

  const w = result?.weather;
  const temp = useCountUp(w?.temperature ?? 0);

  useEffect(() => {
    setReady(false);
    if (!result) return;
    const t = setTimeout(() => setReady(true), 120);
    return () => clearTimeout(t);
  }, [result]);

  const handleSubmit = async () => {
    if (!location.trim()) {
      toast.error('Please enter a location!');
      return;
    }
    setLoading(true);
    try {
      const res = await getWeatherAdvisory(location, selectedDisease || null, selectedSeverity || 'medium');
      setResult(res.data);
      toast.success('Weather & 1-Week Action Plan loaded!');
    } catch (err) {
      toast.error('Location not found. Try another city!');
    }
    setLoading(false);
  };

  const handleClearDisease = () => {
    setSelectedDisease('');
    if (result && location) {
      getWeatherAdvisory(location, null, null).then((res) => setResult(res.data));
    }
  };

  const weeklyPlan = result?.weekly_plan;
  const activeDay = weeklyPlan?.days?.find((d) => d.day_number === activeDayTab) || weeklyPlan?.days?.[0];

  return (
    <div className="wa-root">
      {/* Header */}
      <header className="wa-header">
        <button className="wa-back" onClick={() => navigate('/farmer')}>← Back to Dashboard</button>
        <div className="wa-header-text">
          <h1>🌦️ Weather Advisory</h1>
          <p>Live weather and a 7-day crop disease action plan</p>
        </div>
      </header>

      <main className="wa-main">
        {/* Search panel */}
        <section className="wa-card">
          <h2 className="wa-panel-title">Where are you farming today?</h2>
          <p className="wa-panel-sub">Enter your location to get weather-based farming advice.</p>

          {/* Disease Context Pill / Selector */}
          <label className="wa-field-label">🔬 Disease context</label>
          {selectedDisease && (
            <div className="wa-disease-current">
              <span className="wa-active-disease-badge">
                {selectedDisease}
                <span className={`wa-sev-dot ${selectedSeverity}`}></span>
                <button className="wa-clear-btn" onClick={handleClearDisease} title="Clear Disease Context">✕</button>
              </span>
            </div>
          )}

          <div className="wa-disease-select-row">
            <select
              value={selectedDisease}
              onChange={(e) => setSelectedDisease(e.target.value)}
              className="wa-disease-select"
              aria-label="Select disease context"
            >
              <option value="">-- Choose Disease or General Plan --</option>
              {recentDisease && (
                <option value={recentDisease.full_disease || recentDisease.disease}>
                  ⭐ Recent Scan: {recentDisease.full_disease || recentDisease.disease} ({recentDisease.severity || 'high'})
                </option>
              )}
              {COMMON_DISEASES.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>

            {selectedDisease && (
              <select
                value={selectedSeverity}
                onChange={(e) => setSelectedSeverity(e.target.value)}
                className="wa-disease-select wa-sev-select"
                aria-label="Severity level"
              >
                <option value="high">High Severity</option>
                <option value="medium">Medium Severity</option>
                <option value="low">Low Severity</option>
              </select>
            )}
          </div>

          <div className="wa-search">
            <input
              value={location}
              placeholder="Hyderabad, Chennai, Mumbai, Guntur…"
              onChange={(e) => setLocation(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
              aria-label="Location"
            />
            <button onClick={handleSubmit} disabled={loading}>
              {loading ? (
                <span className="wa-sprout" aria-label="Loading"><i /><i /><i /></span>
              ) : (
                'Get 1-Week Plan'
              )}
            </button>
          </div>
        </section>

        {result && (
          <div className="wa-results" key={w.location + w.temperature}>
            {/* Current weather */}
            <section className="wa-now">
              <div>
                <p className="wa-place">📍 {w.location}</p>
                <h1 className="wa-temp">{Math.round(temp)}<sup>°C</sup></h1>
                <p className="wa-cond">{w.condition}</p>
              </div>
              <div className="wa-stats">
                <div className="wa-stat">
                  <span className="wa-stat-icon">💧</span>
                  <strong>{Math.round(w.humidity)}<small>%</small></strong>
                  <span>Humidity</span>
                </div>
                <div className="wa-stat">
                  <span className="wa-stat-icon">💨</span>
                  <strong>{(Number(w.wind_speed) || 0).toFixed(1)}<small> km/h</small></strong>
                  <span>Wind speed</span>
                </div>
                <div className="wa-stat">
                  <span className="wa-stat-icon">🌧️</span>
                  <strong>{Number(w.rainfall) || 0}<small> mm</small></strong>
                  <span>Rainfall</span>
                </div>
              </div>
            </section>

            {/* Current Day Advisories */}
            <h2 className="wa-h2">
              Today's Farm Alerts <span>{result.total_advisories}</span>
            </h2>

            <div className="wa-list">
              {result.advisories.map((adv, idx) => {
                const isStr = typeof adv === 'string';
                const sevKey = String(adv.severity || 'low').toLowerCase();
                const sev = SEVERITY[sevKey] || SEVERITY.low;
                return (
                  <article
                    key={idx}
                    className="wa-adv"
                    style={{ '--sev': isStr ? '#2f9e5e' : sev.color }}
                  >
                    <span className="wa-adv-icon">{isStr ? '🌱' : (SEVERITY_ICON[sevKey] || '🌱')}</span>
                    <div className="wa-adv-body">
                      <p className="wa-adv-text">{isStr ? adv : adv.message}</p>
                      {!isStr && (
                        <div className="wa-adv-meta">
                          <b>{sev.label} severity</b>
                          {adv.confidence !== undefined && (
                            <>
                              <div className="wa-bar"><div style={{ width: ready ? `${adv.confidence}%` : '0%' }} /></div>
                              <span>{adv.confidence}% confidence</span>
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>

            {/* ═══════════════════════════════════════════════════════
                1-WEEK DISEASE & WEATHER ACTION PLAN SECTION
               ═══════════════════════════════════════════════════════ */}
            {weeklyPlan && (
              <section className="wa-weekly-section">
                <div className="wa-weekly-header">
                  <div>
                    <h2 className="wa-weekly-title">
                      📅 1-Week Disease & Weather Action Plan
                    </h2>
                    <p className="wa-weekly-subtitle">
                      Synchronized for <strong>{weeklyPlan.disease_context}</strong> ({weeklyPlan.disease_severity?.toUpperCase()} SEVERITY)
                    </p>
                  </div>
                  <div className="wa-plan-source-badge">
                    {weeklyPlan.source || 'AI Agronomic Engine'}
                  </div>
                </div>

                {/* Strategic Overview Card */}
                <div className="wa-strategy-card">
                  <div className="wa-strat-item">
                    <span className="wa-strat-icon">🎯</span>
                    <div>
                      <strong>Weekly Strategy</strong>
                      <p>{weeklyPlan.plan_summary}</p>
                    </div>
                  </div>

                  <div className="wa-strat-grid">
                    <div className="wa-strat-subitem">
                      <span className="wa-sub-icon">🧴</span>
                      <div>
                        <strong>Best Spray Windows</strong>
                        <p>{weeklyPlan.best_spray_windows || 'Day 1 & Day 5'}</p>
                      </div>
                    </div>
                    <div className="wa-strat-subitem">
                      <span className="wa-sub-icon">🚿</span>
                      <div>
                        <strong>Irrigation Protocol</strong>
                        <p>{weeklyPlan.irrigation_advice || 'Root drip watering; avoid wetting foliage.'}</p>
                      </div>
                    </div>
                    <div className="wa-strat-subitem">
                      <span className="wa-sub-icon">⚠️</span>
                      <div>
                        <strong>Critical Watch Days</strong>
                        <p>{Array.isArray(weeklyPlan.critical_watch_days) ? weeklyPlan.critical_watch_days.join(', ') : 'Day 3, Day 4'}</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Day Selector Pills */}
                <div className="wa-day-tabs">
                  {weeklyPlan.days?.map((d) => {
                    const sprayCls = d.spray_status === 'optimal' ? 'safe' : d.spray_status === 'caution' ? 'caution' : 'avoid';
                    return (
                      <button
                        key={d.day_number}
                        className={`wa-day-tab ${activeDayTab === d.day_number ? 'active' : ''} ${sprayCls}`}
                        onClick={() => setActiveDayTab(d.day_number)}
                      >
                        <span className="wa-day-tab-num">Day {d.day_number}</span>
                        <span className="wa-day-tab-date">{d.date || `Day ${d.day_number}`}</span>
                        <span className="wa-day-tab-temp">{Math.round(d.temperature)}°C</span>
                        <span className={`wa-day-pill-dot ${sprayCls}`} />
                      </button>
                    );
                  })}
                </div>

                {/* Active Day Detail Card */}
                {activeDay && (
                  <div className="wa-day-detail-card" key={activeDay.day_number}>
                    <div className="wa-day-top-bar">
                      <div className="wa-day-main-info">
                        <span className="wa-day-badge">Day {activeDay.day_number}</span>
                        <h3>{activeDay.day_name}</h3>
                        <span className="wa-day-date-tag">{activeDay.date}</span>
                      </div>

                      <div className={`wa-spray-status-tag ${activeDay.spray_status}`}>
                        {activeDay.spray_label || (activeDay.spray_status === 'optimal' ? '✅ Optimal Spray Window' : activeDay.spray_status === 'caution' ? '⚠️ Caution / Early Morning' : '❌ Avoid Outdoor Spraying')}
                      </div>
                    </div>

                    {/* Daily Weather Snapshot Grid */}
                    <div className="wa-weather-snapshot">
                      <div className="wa-snap-box">
                        <span>Condition</span>
                        <strong>{activeDay.condition || 'Partly Cloudy'}</strong>
                      </div>
                      <div className="wa-snap-box">
                        <span>Avg Temp</span>
                        <strong>{activeDay.temperature}°C</strong>
                      </div>
                      <div className="wa-snap-box">
                        <span>Humidity</span>
                        <strong>{activeDay.humidity}%</strong>
                      </div>
                      <div className="wa-snap-box">
                        <span>Wind Speed</span>
                        <strong>{activeDay.wind_speed} km/h</strong>
                      </div>
                      <div className="wa-snap-box">
                        <span>Rainfall</span>
                        <strong>{activeDay.rainfall} mm ({activeDay.rain_probability || 0}%)</strong>
                      </div>
                    </div>

                    {/* Day Action Items */}
                    <div className="wa-day-action-body">
                      <div className="wa-action-focus">
                        <span className="wa-focus-label">KEY FOCUS</span>
                        <span className="wa-focus-val">{activeDay.key_focus || 'Treatment & Scouting'}</span>
                      </div>

                      <h4 className="wa-action-headline">{activeDay.action_title}</h4>
                      <p className="wa-action-desc">{activeDay.action_description}</p>

                      {activeDay.precautions && (
                        <div className="wa-action-warning">
                          <strong>⚠️ Precaution:</strong> {activeDay.precautions}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Full 7-Day Timeline Cards Overview */}
                <div className="wa-timeline-grid">
                  {weeklyPlan.days?.map((d) => (
                    <div
                      key={d.day_number}
                      className={`wa-timeline-card ${activeDayTab === d.day_number ? 'highlighted' : ''}`}
                      onClick={() => setActiveDayTab(d.day_number)}
                    >
                      <div className="wa-tc-header">
                        <strong>Day {d.day_number}</strong>
                        <span className={`wa-tc-spray ${d.spray_status}`}>{d.spray_status.toUpperCase()}</span>
                      </div>
                      <p className="wa-tc-cond">{d.condition} • {d.temperature}°C</p>
                      <p className="wa-tc-title">{d.action_title}</p>
                      <p className="wa-tc-desc">{d.action_description?.slice(0, 100)}…</p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Weather API Key Integration Note */}
            <div className="wa-api-helper-card">
              <div className="wa-api-helper-icon">⚡</div>
              <div className="wa-api-helper-text">
                <strong>Live Weather API Ready:</strong>
                <p>
                  To connect real-time satellite radar and forecast data from OpenWeatherMap, add your key in <code>backend/.env</code> as:
                  <br />
                  <code>WEATHER_API_KEY=your_openweathermap_key</code>
                </p>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}