import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { getCropRecommendation } from '../services/api';
import toast from 'react-hot-toast';

/* ═══════════════════════════════════════════════════════════════
   ALIP — Crop Recommendation  (Farmer Dashboard)
   Light mode · Glassmorphism · Step wizard · Rich animations
═══════════════════════════════════════════════════════════════ */

// ── Constants ─────────────────────────────────────────────────
const SEASONS = [
  { value: 'kharif', label: 'Kharif',  icon: '🌧️', period: 'Jun – Nov', grad: 'linear-gradient(135deg,#0ea5e9,#38bdf8)', shadow: 'rgba(14,165,233,0.35)' },
  { value: 'rabi',   label: 'Rabi',    icon: '❄️',  period: 'Nov – Apr', grad: 'linear-gradient(135deg,#8b5cf6,#a78bfa)', shadow: 'rgba(139,92,246,0.35)' },
  { value: 'zaid',   label: 'Zaid',    icon: '☀️',  period: 'Apr – Jun', grad: 'linear-gradient(135deg,#f59e0b,#fbbf24)', shadow: 'rgba(245,158,11,0.35)' },
];

const ADVANCED_FIELDS = [
  { key: 'nitrogen',    label: 'Nitrogen (N)',    unit: 'kg/ha', min: 0,   max: 140, placeholder: '80',  icon: '🧪', color: '#16a34a', bg: '#dcfce7' },
  { key: 'phosphorous', label: 'Phosphorous (P)', unit: 'kg/ha', min: 0,   max: 145, placeholder: '40',  icon: '⚗️', color: '#ea580c', bg: '#ffedd5' },
  { key: 'potassium',   label: 'Potassium (K)',   unit: 'kg/ha', min: 0,   max: 205, placeholder: '40',  icon: '🔬', color: '#7c3aed', bg: '#ede9fe' },
  { key: 'ph',          label: 'Soil pH',         unit: '',      min: 3.5, max: 10,  placeholder: '6.5', icon: '🧫', color: '#dc2626', bg: '#fee2e2' },
  { key: 'temperature', label: 'Temperature',     unit: '°C',    min: 0,   max: 50,  placeholder: '28',  icon: '🌡️', color: '#d97706', bg: '#fef3c7' },
  { key: 'humidity',    label: 'Humidity',        unit: '%',     min: 0,   max: 100, placeholder: '80',  icon: '💧', color: '#0284c7', bg: '#e0f2fe' },
  { key: 'rainfall',    label: 'Rainfall',        unit: 'mm',    min: 20,  max: 300, placeholder: '200', icon: '🌧️', color: '#0891b2', bg: '#cffafe' },
];

const CROP_EMOJIS = {
  rice:'🌾', wheat:'🌾', maize:'🌽', cotton:'🌿', sugarcane:'🎋',
  jute:'🌿', coffee:'☕', tea:'🍵', banana:'🍌', mango:'🥭',
  grapes:'🍇', watermelon:'🍉', muskmelon:'🍈', apple:'🍎',
  orange:'🍊', papaya:'🫒', coconut:'🥥', pomegranate:'🍎',
  lentil:'🫘', chickpea:'🫘', kidneybeans:'🫘', pigeonpeas:'🫘',
  mothbeans:'🫘', mungbean:'🫘', blackgram:'🫘',
};
const getCropEmoji = n => CROP_EMOJIS[n?.toLowerCase().replace(/\s+/g,'')] || '🌱';

const RANK_CONFIG = [
  { medal:'🥇', label:'Best Match',   grad:'linear-gradient(135deg,#f59e0b,#fbbf24)', shadow:'rgba(245,158,11,0.4)',  ring:'#f59e0b', trackBg:'#fef3c7' },
  { medal:'🥈', label:'2nd Choice',   grad:'linear-gradient(135deg,#64748b,#94a3b8)', shadow:'rgba(100,116,139,0.3)', ring:'#64748b', trackBg:'#f1f5f9' },
  { medal:'🥉', label:'3rd Choice',   grad:'linear-gradient(135deg,#b45309,#d97706)', shadow:'rgba(180,83,9,0.3)',    ring:'#b45309', trackBg:'#fef3c7' },
];

const WEATHER_LABEL = {
  'openweathermap':    { icon:'🌐', text:'Live Weather',      color:'#0284c7' },
  'user-provided':     { icon:'✏️',  text:'Your Field Data',   color:'#16a34a' },
  'mixed-user-provided':{ icon:'✏️', text:'Field + Estimates', color:'#d97706' },
  'fallback-regional': { icon:'📍',  text:'Regional Estimate', color:'#d97706' },
  'demo-fallback':     { icon:'📍',  text:'Weather Estimate',  color:'#d97706' },
};

const SOIL_LABEL = {
  'user-provided':        'Your soil inputs',
  'mixed-user-provided':  'Your inputs + location estimate',
  'regional estimate':    'Regional soil estimate',
  'general estimate':     'General soil estimate',
};

const RAINFALL_LABEL = {
  'user-provided':    'Your field input',
  'seasonal estimate':'Seasonal estimate',
};

// ── Animated confidence ring ───────────────────────────────────
function ConfRing({ value, config, delay = 0 }) {
  const [pct, setPct] = useState(0);
  const [num, setNum] = useState(0);
  const circumference = 2 * Math.PI * 20;

  useEffect(() => {
    const t1 = setTimeout(() => {
      setPct(value);
      let s = 0, step = Math.ceil(value / 40);
      const iv = setInterval(() => {
        s = Math.min(s + step, value);
        setNum(s);
        if (s >= value) clearInterval(iv);
      }, 25);
    }, 400 + delay);
    return () => clearTimeout(t1);
  }, [value, delay]);

  const confColor = value >= 80 ? '#16a34a' : value >= 60 ? '#d97706' : '#dc2626';
  const fillDash  = (pct / 100) * circumference;

  return (
    <div style={{ ...rs.ringWrap, background: config.trackBg }}>
      <svg width="72" height="72" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx="36" cy="36" r="20" fill="none" stroke="#e2e8f0" strokeWidth="5" />
        <circle
          cx="36" cy="36" r="20" fill="none"
          stroke={confColor} strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={`${fillDash} ${circumference}`}
          style={{ transition: 'stroke-dasharray 1.2s cubic-bezier(0.34,1.2,0.64,1)' }}
        />
      </svg>
      <div style={rs.ringLabel}>
        <span style={{ ...rs.ringNum, color: confColor }}>{num}</span>
        <span style={rs.ringPct}>%</span>
      </div>
    </div>
  );
}

// ── Horizontal bar ─────────────────────────────────────────────
function ConfBar({ value, delay = 0 }) {
  const [w, setW] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => setW(value), 500 + delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  const c = value >= 80 ? '#16a34a' : value >= 60 ? '#d97706' : '#dc2626';
  return (
    <div style={rs.barTrack}>
      <div style={{
        ...rs.barFill,
        width: `${w}%`,
        background: `linear-gradient(90deg,${c},${c}aa)`,
        transition: 'width 1s cubic-bezier(0.34,1.1,0.64,1)',
      }} />
    </div>
  );
}

// ── Floating leaf particles ────────────────────────────────────
function Particles() {
  const items = Array.from({ length: 14 }, (_, i) => ({
    emoji: ['🌿','🍃','🌱','🌾','🍀'][i % 5],
    left:  `${(i * 7.2) % 100}%`,
    delay: `${(i * 0.9) % 12}s`,
    dur:   `${14 + (i % 5) * 2}s`,
    size:  `${12 + (i % 4) * 3}px`,
    op:    0.12 + (i % 3) * 0.05,
  }));
  return (
    <div style={rs.particles} aria-hidden="true">
      {items.map((p, i) => (
        <span key={i} style={{
          ...rs.particle,
          left: p.left, fontSize: p.size, opacity: p.op,
          animation: `floatUp ${p.dur} linear ${p.delay} infinite`,
        }}>{p.emoji}</span>
      ))}
      <style>{`
        @keyframes floatUp {
          0%   { transform: translateY(100vh) rotate(0deg); opacity: 0; }
          10%  { opacity: 1; }
          90%  { opacity: 0.6; }
          100% { transform: translateY(-120px) rotate(360deg); opacity: 0; }
        }
        @keyframes fadeSlideUp {
          from { opacity: 0; transform: translateY(28px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeScaleIn {
          from { opacity: 0; transform: scale(0.94) translateY(16px); }
          to   { opacity: 1; transform: scale(1) translateY(0); }
        }
        @keyframes shimmer {
          0%   { background-position: -200% 0; }
          100% { background-position:  200% 0; }
        }
        @keyframes pulse {
          0%,100% { opacity: 1; transform: scale(1); }
          50%     { opacity: 0.7; transform: scale(0.95); }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        @keyframes badgePop {
          0%   { transform: scale(0); }
          70%  { transform: scale(1.2); }
          100% { transform: scale(1); }
        }
        @keyframes gradShift {
          0%,100% { background-position: 0% 50%; }
          50%     { background-position: 100% 50%; }
        }
      `}</style>
    </div>
  );
}

// ── Step indicator ─────────────────────────────────────────────
function StepBar({ step }) {
  const steps = ['Location', 'Season', 'Soil Data', 'Results'];
  return (
    <div style={rs.stepBar}>
      {steps.map((label, i) => {
        const done    = i < step;
        const active  = i === step;
        return (
          <React.Fragment key={i}>
            <div style={rs.stepItem}>
              <div style={{
                ...rs.stepCircle,
                ...(done   ? rs.stepDone   : {}),
                ...(active ? rs.stepActive : {}),
              }}>
                {done ? '✓' : i + 1}
              </div>
              <span style={{
                ...rs.stepLabel,
                color: active ? '#15803d' : done ? '#16a34a' : '#9ca3af',
                fontWeight: active || done ? 700 : 400,
              }}>{label}</span>
            </div>
            {i < steps.length - 1 && (
              <div style={{
                ...rs.stepLine,
                background: done ? '#16a34a' : '#e5e7eb',
              }} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────
export default function CropRecommendation() {
  const navigate = useNavigate();
  const [step, setStep]             = useState(0);
  const [form, setForm]             = useState({ location: '', season: 'kharif' });
  const [advanced, setAdvanced]     = useState({
    nitrogen:'', phosphorous:'', potassium:'',
    ph:'', temperature:'', humidity:'', rainfall:'',
  });
  const [showAdv, setShowAdv]       = useState(false);
  const [result, setResult]         = useState(null);
  const [loading, setLoading]       = useState(false);
  const [revealed, setRevealed]     = useState(false);
  const [activeRec, setActiveRec]   = useState(0);
  const resultRef = useRef(null);

  const activeSeason = SEASONS.find(s => s.value === form.season);

  const handleSubmit = async () => {
    if (!form.location.trim()) { toast.error('📍 Please enter your location!'); return; }
    const payload = { location: form.location.trim(), season: form.season };
    ADVANCED_FIELDS.forEach(({ key }) => {
      const v = advanced[key];
      if (v !== '' && v != null) payload[key] = parseFloat(v);
    });
    setLoading(true); setRevealed(false);
    try {
      const res = await getCropRecommendation(payload);
      setResult(res.data);
      toast.success('🌱 Recommendation ready!');
      setStep(3);
      setTimeout(() => {
        setRevealed(true);
        resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 150);
    } catch (err) {
      const detail = err.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Something went wrong. Check your inputs.');
    }
    setLoading(false);
  };

  const weatherBadge = result
    ? WEATHER_LABEL[result.weather_source] || { icon:'ℹ️', text: result.weather_source, color:'#6b7280' }
    : null;

  return (
    <div style={rs.page}>
      <Particles />

      {/* ═══ HERO HEADER ═══ */}
      <div style={rs.header}>
        <div style={rs.headerBgBlob1} />
        <div style={rs.headerBgBlob2} />
        <div style={rs.headerInner}>
          {/* Back */}
          <button style={rs.backBtn} onClick={() => navigate('/farmer')}>
            ← Back
          </button>

          {/* Centre */}
          <div style={rs.headerCenter}>
            <div style={rs.headerIconRing}>
              <div style={rs.headerIconInner}>🌱</div>
            </div>
            <div>
              <div style={rs.headerTag}>
                <span style={rs.tagDot} />
                AI-Powered · ALIP Farmer Module
              </div>
              <h1 style={rs.headerTitle}>Crop Recommendation</h1>
              <p style={rs.headerSub}>Smart planting advice tailored to your field</p>
            </div>
          </div>

          {/* Badge */}
          <div style={rs.mlBadge}>
            <span style={rs.mlDot} />
            ML Model
          </div>
        </div>

        {/* Step bar */}
        <div style={rs.stepBarWrap}>
          <StepBar step={step} />
        </div>
      </div>

      {/* ═══ BODY ═══ */}
      <div style={rs.body}>
        <div style={rs.grid}>

          {/* ══ LEFT: Input Panel ══ */}
          <div style={rs.inputPanel}>

            {/* ── STEP 1: Location ── */}
            <div style={{ ...rs.card, animation: 'fadeSlideUp 0.5s ease both' }}>
              <div style={rs.cardStrip} />
              <div style={rs.stepNumTag}>
                <span style={rs.stepNumBubble}>1</span>
                <span style={rs.stepNumLabel}>Your Location</span>
              </div>
              <h3 style={rs.cardTitle}>📍 Where is your farm?</h3>
              <p style={rs.cardSub}>
                We use this to fetch live weather and estimate soil conditions for your region.
              </p>
              <div style={rs.locationInputWrap}>
                <span style={rs.locationPin}>📍</span>
                <input
                  style={rs.locationInput}
                  placeholder="e.g. Hyderabad, Punjab, Kerala…"
                  value={form.location}
                  onChange={e => { setForm({ ...form, location: e.target.value }); setStep(Math.max(step, 0)); }}
                  onFocus={() => setStep(0)}
                  onKeyDown={e => e.key === 'Enter' && handleSubmit()}
                />
                {form.location && (
                  <button style={rs.clearBtn} onClick={() => setForm({ ...form, location: '' })}>✕</button>
                )}
              </div>
              {/* Quick locations */}
              <div style={rs.quickRow}>
                {['Hyderabad','Punjab','Kerala','Tamil Nadu','Maharashtra','Gujarat'].map(c => (
                  <button key={c} style={{
                    ...rs.quickPill,
                    ...(form.location === c ? rs.quickPillActive : {}),
                  }} onClick={() => { setForm({ ...form, location: c }); setStep(Math.max(step, 1)); }}>
                    {c}
                  </button>
                ))}
              </div>
            </div>

            {/* ── STEP 2: Season ── */}
            <div style={{ ...rs.card, animation: 'fadeSlideUp 0.55s ease 0.08s both' }}>
              <div style={rs.cardStrip} />
              <div style={rs.stepNumTag}>
                <span style={rs.stepNumBubble}>2</span>
                <span style={rs.stepNumLabel}>Growing Season</span>
              </div>
              <h3 style={rs.cardTitle}>🗓️ When will you plant?</h3>
              <p style={rs.cardSub}>
                Your growing season determines which crops are best suited to current conditions.
              </p>
              <div style={rs.seasonGrid}>
                {SEASONS.map(s => {
                  const active = form.season === s.value;
                  return (
                    <button
                      key={s.value}
                      style={{
                        ...rs.seasonBtn,
                        ...(active ? {
                          background: s.grad,
                          boxShadow: `0 8px 24px ${s.shadow}`,
                          border: '2px solid transparent',
                          transform: 'translateY(-4px)',
                        } : {}),
                      }}
                      onClick={() => { setForm({ ...form, season: s.value }); setStep(Math.max(step, 1)); }}
                    >
                      {active && <div style={rs.seasonActiveBg} />}
                      <span style={rs.seasonIcon}>{s.icon}</span>
                      <span style={{ ...rs.seasonLabel, color: active ? '#fff' : '#1e293b' }}>{s.label}</span>
                      <span style={{ ...rs.seasonPeriod, color: active ? 'rgba(255,255,255,0.85)' : '#6b7280' }}>
                        {s.period}
                      </span>
                      {active && <span style={rs.seasonCheck}>✓</span>}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* ── STEP 3: Advanced ── */}
            <div style={{ ...rs.card, animation: 'fadeSlideUp 0.6s ease 0.15s both' }}>
              <div style={rs.cardStrip} />
              <div style={rs.stepNumTag}>
                <span style={rs.stepNumBubble}>3</span>
                <span style={rs.stepNumLabel}>Soil &amp; Climate <span style={rs.optionalTag}>optional</span></span>
              </div>
              <button
                style={rs.advToggle}
                onClick={() => setShowAdv(p => !p)}
              >
                <div style={rs.advToggleLeft}>
                  <span style={rs.advToggleIcon}>⚗️</span>
                  <div>
                    <div style={rs.advToggleTitle}>Advanced Inputs</div>
                    <div style={rs.advToggleSub}>Nitrogen, pH, temperature, humidity…</div>
                  </div>
                </div>
                <span style={{
                  ...rs.advChevron,
                  transform: showAdv ? 'rotate(180deg)' : 'rotate(0deg)',
                }}>▼</span>
              </button>

              {showAdv && (
                <div style={rs.advPanel}>
                  <div style={rs.advHint}>
                    💡 Leave blank to use auto-detected values. Fill in what you know for more precise results.
                  </div>
                  <div style={rs.advGrid}>
                    {ADVANCED_FIELDS.map(f => (
                      <div key={f.key} style={{ ...rs.advField, background: f.bg, borderColor: `${f.color}30` }}>
                        <label style={{ ...rs.advLabel, color: f.color }}>
                          {f.icon} {f.label}
                          {f.unit && <span style={rs.advUnit}>{f.unit}</span>}
                        </label>
                        <input
                          type="number" min={f.min} max={f.max} step="0.1"
                          placeholder={f.placeholder}
                          style={{ ...rs.advInput, borderColor: `${f.color}40`, outlineColor: f.color }}
                          value={advanced[f.key]}
                          onChange={e => setAdvanced({ ...advanced, [f.key]: e.target.value })}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* ── SUBMIT ── */}
            <button
              style={{
                ...rs.submitBtn,
                ...(loading ? rs.submitLoading : {}),
                animation: 'fadeSlideUp 0.65s ease 0.22s both',
              }}
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span style={rs.spinner} />
                  Analysing your field…
                </>
              ) : (
                <>
                  <span style={rs.submitIcon}>🌱</span>
                  Get My Crop Recommendation
                  <span style={rs.submitArrow}>→</span>
                </>
              )}
            </button>
          </div>

          {/* ══ RIGHT: Results Panel ══ */}
          <div>

            {/* ── Results ── */}
            {result && (
              <div
                ref={resultRef}
                style={{
                  ...rs.resultsPanel,
                  animation: revealed ? 'fadeScaleIn 0.55s cubic-bezier(0.34,1.1,0.64,1) both' : 'none',
                  opacity: revealed ? 1 : 0,
                }}
              >

                {/* Top strip */}
                <div style={rs.resultsHeader}>
                  <div style={rs.resultsHeaderBg} />
                  <div style={rs.resultsHeaderContent}>
                    <div style={rs.resultsHeaderLeft}>
                      <div style={rs.resultsEmoji}>🎯</div>
                      <div>
                        <div style={rs.resultsTag}>Results ready</div>
                        <div style={rs.resultsTitle}>Top Recommendations</div>
                      </div>
                    </div>
                    {weatherBadge && (
                      <div style={{ ...rs.sourcePill, borderColor: `${weatherBadge.color}40`, color: weatherBadge.color, background: `${weatherBadge.color}10` }}>
                        {weatherBadge.icon} {weatherBadge.text}
                      </div>
                    )}
                  </div>
                </div>

                {/* Field context */}
                <div style={rs.contextGrid}>
                  {[
                    { icon:'📍', label:'Region',      value: result.soil_type || '—' },
                    { icon:'🌡️', label:'Temperature', value: result.weather_inputs?.temperature != null ? `${result.weather_inputs.temperature}°C` : 'N/A' },
                    { icon:'💧', label:'Humidity',    value: result.weather_inputs?.humidity != null ? `${result.weather_inputs.humidity}%` : 'N/A' },
                    { icon:'🌧️', label:'Rainfall',   value: `${result.weather_inputs?.rainfall || 0} mm` },
                    { icon:'🧪', label:'Nitrogen',    value: `${result.soil_summary?.nitrogen || '—'} kg/ha` },
                    { icon:'🧫', label:'Soil pH',     value: result.soil_summary?.ph || '—' },
                  ].map((item, i) => (
                    <div key={i} style={{
                      ...rs.contextCard,
                      animation: `fadeSlideUp 0.4s ease ${i * 0.07}s both`,
                    }}>
                      <span style={rs.contextIcon}>{item.icon}</span>
                      <span style={rs.contextVal}>{item.value}</span>
                      <span style={rs.contextLbl}>{item.label}</span>
                    </div>
                  ))}
                </div>

                {/* Source notes */}
                <div style={rs.sourceNote}>
                  🌍 Soil: {SOIL_LABEL[result.soil_source] || result.soil_source}
                  &nbsp;·&nbsp;
                  🌧️ Rainfall: {RAINFALL_LABEL[result.rainfall_source] || result.rainfall_source}
                </div>

                {/* Crop tab selector */}
                <div style={rs.tabRow}>
                  {result.recommendations.map((rec, i) => {
                    const cfg = RANK_CONFIG[i] || RANK_CONFIG[2];
                    return (
                      <button
                        key={i}
                        style={{
                          ...rs.tabBtn,
                          ...(activeRec === i ? {
                            background: cfg.grad,
                            color: '#fff',
                            boxShadow: `0 6px 18px ${cfg.shadow}`,
                            transform: 'translateY(-2px)',
                          } : {}),
                        }}
                        onClick={() => setActiveRec(i)}
                      >
                        {cfg.medal} {rec.crop.charAt(0).toUpperCase() + rec.crop.slice(1)}
                      </button>
                    );
                  })}
                </div>

                {/* Active recommendation detail */}
                {result.recommendations[activeRec] && (() => {
                  const rec = result.recommendations[activeRec];
                  const cfg = RANK_CONFIG[activeRec] || RANK_CONFIG[2];
                  return (
                    <div style={{
                      ...rs.recDetail,
                      animation: 'fadeScaleIn 0.35s ease both',
                    }} key={activeRec}>

                      {/* Hero row */}
                      <div style={{ ...rs.recHero, background: cfg.grad, boxShadow: `0 12px 30px ${cfg.shadow}` }}>
                        <div style={rs.recHeroBg} />
                        <div style={rs.recHeroLeft}>
                          <div style={rs.recCropEmoji}>{getCropEmoji(rec.crop)}</div>
                          <div>
                            <div style={rs.recMedalBadge}>{cfg.label}</div>
                            <div style={rs.recCropName}>
                              {rec.crop.charAt(0).toUpperCase() + rec.crop.slice(1)}
                            </div>
                            <div style={rs.recCropDesc}>{rec.description}</div>
                          </div>
                        </div>
                        {rec.confidence != null && (
                          <ConfRing value={rec.confidence} config={cfg} delay={activeRec * 100} />
                        )}
                      </div>

                      {/* Confidence bar */}
                      {rec.confidence != null && (
                        <div style={rs.confBarWrap}>
                          <div style={rs.confBarLabel}>
                            <span>Model match score</span>
                            <span style={{ fontWeight: 700 }}>{rec.confidence}%</span>
                          </div>
                          <ConfBar value={rec.confidence} delay={activeRec * 100} />
                        </div>
                      )}

                      {rec.confidence == null && (
                        <div style={rs.regionalTag}>
                          📍 Regional seasonal option — no model score available
                        </div>
                      )}
                    </div>
                  );
                })()}

                {/* All 3 mini cards */}
                <div style={rs.miniGrid}>
                  {result.recommendations.map((rec, i) => {
                    const cfg = RANK_CONFIG[i] || RANK_CONFIG[2];
                    return (
                      <div
                        key={i}
                        style={{
                          ...rs.miniCard,
                          borderTopColor: cfg.ring,
                          animation: `fadeSlideUp 0.4s ease ${0.35 + i * 0.1}s both`,
                          cursor: 'pointer',
                          outline: activeRec === i ? `2px solid ${cfg.ring}` : 'none',
                        }}
                        onClick={() => setActiveRec(i)}
                      >
                        <div style={rs.miniTop}>
                          <span style={rs.miniEmoji}>{getCropEmoji(rec.crop)}</span>
                          <span style={{ ...rs.miniMedal, animation: 'badgePop 0.4s ease both' }}>
                            {cfg.medal}
                          </span>
                        </div>
                        <div style={rs.miniName}>
                          {rec.crop.charAt(0).toUpperCase() + rec.crop.slice(1)}
                        </div>
                        {rec.confidence != null ? (
                          <div style={{ ...rs.miniConf, color: rec.confidence >= 80 ? '#16a34a' : rec.confidence >= 60 ? '#d97706' : '#dc2626' }}>
                            {rec.confidence}% match
                          </div>
                        ) : (
                          <div style={{ ...rs.miniConf, color: '#6b7280' }}>Regional pick</div>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Disclaimer */}
                <div style={rs.disclaimer}>
                  <span style={rs.disclaimerIcon}>💡</span>
                  <p style={rs.disclaimerText}>
                    Match scores are model rankings, not yield guarantees.
                    Soil and rainfall values may be regional estimates unless marked as your inputs.
                    Always validate with a soil test and consult a local agronomist before planting.
                  </p>
                </div>

              </div>
            )}

            {/* ── Empty state ── */}
            {!result && !loading && (
              <div style={{ ...rs.emptyState, animation: 'fadeSlideUp 0.6s ease 0.3s both' }}>
                <div style={rs.emptyOrb} />
                <div style={rs.emptyEmoji}>🌾</div>
                <div style={rs.emptyTitle}>Your recommendation will appear here</div>
                <p style={rs.emptySub}>
                  Fill in your location and season on the left, then click
                  "Get My Crop Recommendation".
                </p>
                <div style={rs.emptySteps}>
                  {['Enter your location','Choose a season','Click Recommend'].map((s, i) => (
                    <div key={i} style={rs.emptyStep}>
                      <div style={rs.emptyStepNum}>{i + 1}</div>
                      <span style={rs.emptyStepLabel}>{s}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── Loading state ── */}
            {loading && (
              <div style={rs.loadingState}>
                <div style={rs.loadingRing}>
                  <div style={rs.loadingInnerRing} />
                  <span style={rs.loadingEmoji}>🌱</span>
                </div>
                <div style={rs.loadingTitle}>Analysing your field…</div>
                <div style={rs.loadingSteps}>
                  {['Fetching weather data','Estimating soil profile','Running ML model','Ranking crops'].map((s, i) => (
                    <div key={i} style={{ ...rs.loadingStep, animationDelay: `${i * 0.4}s` }}>
                      <div style={rs.loadingDot} />
                      {s}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   STYLES
═══════════════════════════════════════════════════════════════ */
const rs = {
  /* PAGE */
  page: {
    minHeight: '100vh',
    background: 'linear-gradient(160deg,#f0fdf4 0%,#f8fafc 50%,#ecfdf5 100%)',
    fontFamily: "'Segoe UI','Outfit',sans-serif",
    color: '#1e293b',
    overflowX: 'hidden',
    position: 'relative',
  },

  /* PARTICLES */
  particles: { position:'fixed', inset:0, pointerEvents:'none', zIndex:0, overflow:'hidden' },
  particle:  { position:'absolute', bottom:'-60px', userSelect:'none' },

  /* HEADER */
  header: {
    position: 'sticky', top: 0, zIndex: 100,
    background: 'rgba(255,255,255,0.88)',
    backdropFilter: 'blur(20px)',
    borderBottom: '1px solid #d1fae5',
    boxShadow: '0 2px 20px rgba(22,163,74,0.08)',
    paddingBottom: '0.5rem',
  },
  headerBgBlob1: {
    position: 'absolute', top: -40, left: -40,
    width: 200, height: 200, borderRadius: '50%',
    background: 'radial-gradient(circle,rgba(134,239,172,0.18) 0%,transparent 70%)',
    pointerEvents: 'none',
  },
  headerBgBlob2: {
    position: 'absolute', top: -20, right: -20,
    width: 160, height: 160, borderRadius: '50%',
    background: 'radial-gradient(circle,rgba(187,247,208,0.15) 0%,transparent 70%)',
    pointerEvents: 'none',
  },
  headerInner: {
    maxWidth: 1200, margin: '0 auto',
    padding: '1rem 2rem',
    display: 'flex', alignItems: 'center',
    justifyContent: 'space-between', gap: '1rem',
    position: 'relative', zIndex: 1,
  },
  backBtn: {
    background: '#f0fdf4', border: '1.5px solid #bbf7d0',
    color: '#15803d', borderRadius: 100,
    padding: '0.42rem 1.1rem',
    fontSize: '0.78rem', fontWeight: 700, cursor: 'pointer',
    whiteSpace: 'nowrap', transition: 'all 0.2s',
  },
  headerCenter: { display:'flex', alignItems:'center', gap:'1rem', flex:1, justifyContent:'center' },
  headerIconRing: {
    width: 52, height: 52, borderRadius: '50%',
    background: 'linear-gradient(135deg,#bbf7d0,#86efac)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 6px 18px rgba(22,163,74,0.3)',
    flexShrink: 0,
  },
  headerIconInner: { fontSize: '1.5rem' },
  headerTag: {
    fontSize: '0.6rem', letterSpacing: '0.18em',
    textTransform: 'uppercase', color: '#16a34a',
    display: 'flex', alignItems: 'center', gap: '0.4rem',
    marginBottom: '0.1rem',
  },
  tagDot: {
    display: 'inline-block', width: 6, height: 6,
    borderRadius: '50%', background: '#22c55e',
    animation: 'pulse 2s ease infinite',
  },
  headerTitle: {
    margin: 0, fontSize: 'clamp(1rem,2.5vw,1.4rem)',
    fontWeight: 900, color: '#14532d',
  },
  headerSub: { fontSize: '0.78rem', color: '#6b7280', margin: 0 },
  mlBadge: {
    background: 'linear-gradient(135deg,#dcfce7,#bbf7d0)',
    border: '1px solid #86efac',
    borderRadius: 100, padding: '0.38rem 0.9rem',
    fontSize: '0.72rem', fontWeight: 700, color: '#15803d',
    display: 'flex', alignItems: 'center', gap: '0.4rem',
    whiteSpace: 'nowrap',
  },
  mlDot: {
    width: 7, height: 7, borderRadius: '50%',
    background: '#22c55e', animation: 'pulse 1.5s ease infinite',
  },

  /* STEP BAR */
  stepBarWrap: {
    maxWidth: 1200, margin: '0 auto',
    padding: '0 2rem 0.6rem',
  },
  stepBar: {
    display: 'flex', alignItems: 'center',
    gap: 0, maxWidth: 500,
  },
  stepItem: {
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', gap: '0.2rem',
    minWidth: 70,
  },
  stepCircle: {
    width: 28, height: 28, borderRadius: '50%',
    background: '#e5e7eb', color: '#9ca3af',
    fontSize: '0.72rem', fontWeight: 700,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    transition: 'all 0.4s ease',
  },
  stepDone: {
    background: '#16a34a', color: '#fff',
    boxShadow: '0 3px 10px rgba(22,163,74,0.4)',
  },
  stepActive: {
    background: 'linear-gradient(135deg,#16a34a,#22c55e)',
    color: '#fff', transform: 'scale(1.15)',
    boxShadow: '0 4px 14px rgba(22,163,74,0.45)',
  },
  stepLabel: { fontSize: '0.62rem', transition: 'all 0.3s' },
  stepLine: {
    flex: 1, height: 2, borderRadius: 1,
    transition: 'background 0.5s ease',
    marginBottom: 18,
  },

  /* BODY */
  body: {
    position: 'relative', zIndex: 1,
    maxWidth: 1200, margin: '0 auto',
    padding: '2rem 2rem 5rem',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: '420px 1fr',
    gap: '1.5rem',
    alignItems: 'start',
  },

  /* CARDS */
  card: {
    background: '#ffffff',
    border: '1.5px solid #d1fae5',
    borderRadius: 20,
    padding: '1.6rem',
    marginBottom: '1.2rem',
    boxShadow: '0 4px 24px rgba(22,163,74,0.07)',
    position: 'relative', overflow: 'hidden',
  },
  cardStrip: {
    position: 'absolute', top: 0, left: 0, right: 0,
    height: 3,
    background: 'linear-gradient(90deg,#16a34a,#84cc16,#22c55e)',
  },
  stepNumTag: {
    display: 'flex', alignItems: 'center', gap: '0.5rem',
    marginBottom: '0.7rem',
  },
  stepNumBubble: {
    width: 22, height: 22, borderRadius: '50%',
    background: 'linear-gradient(135deg,#16a34a,#22c55e)',
    color: '#fff', fontSize: '0.68rem', fontWeight: 900,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 2px 8px rgba(22,163,74,0.4)',
  },
  stepNumLabel: {
    fontSize: '0.68rem', fontWeight: 700,
    letterSpacing: '0.12em', textTransform: 'uppercase', color: '#16a34a',
  },
  optionalTag: {
    background: '#dcfce7', color: '#15803d',
    borderRadius: 100, padding: '0.1rem 0.5rem',
    fontSize: '0.58rem', fontWeight: 700,
    letterSpacing: '0.06em', marginLeft: '0.3rem',
  },
  cardTitle: { margin: '0 0 0.3rem', fontSize: '1.05rem', fontWeight: 800, color: '#14532d' },
  cardSub:   { margin: '0 0 1rem',   fontSize: '0.82rem', color: '#6b7280', lineHeight: 1.6 },

  /* LOCATION INPUT */
  locationInputWrap: {
    display: 'flex', alignItems: 'center', gap: '0',
    background: '#f8fffe',
    border: '1.5px solid #86efac',
    borderRadius: 12,
    overflow: 'hidden',
    boxShadow: '0 2px 10px rgba(22,163,74,0.1)',
    marginBottom: '0.9rem',
  },
  locationPin: {
    padding: '0 0.75rem', fontSize: '1.1rem',
    background: '#f0fdf4', borderRight: '1px solid #d1fae5',
    alignSelf: 'stretch', display: 'flex', alignItems: 'center',
  },
  locationInput: {
    flex: 1, padding: '0.8rem 0.85rem',
    border: 'none', outline: 'none',
    background: 'transparent',
    fontSize: '0.95rem', color: '#1e293b', fontFamily: 'inherit',
  },
  clearBtn: {
    padding: '0 0.85rem', background: 'none',
    border: 'none', color: '#9ca3af', cursor: 'pointer',
    fontSize: '0.85rem',
  },

  /* QUICK PILLS */
  quickRow: { display:'flex', flexWrap:'wrap', gap:'0.45rem' },
  quickPill: {
    background: '#f0fdf4', border: '1px solid #bbf7d0',
    borderRadius: 100, padding: '0.25rem 0.75rem',
    fontSize: '0.73rem', color: '#15803d',
    cursor: 'pointer', fontWeight: 600, fontFamily: 'inherit',
    transition: 'all 0.2s',
  },
  quickPillActive: {
    background: '#16a34a', border: '1px solid #16a34a',
    color: '#fff', boxShadow: '0 3px 10px rgba(22,163,74,0.35)',
  },

  /* SEASON */
  seasonGrid: { display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:'0.7rem' },
  seasonBtn: {
    background: '#f9fafb', border: '2px solid #e5e7eb',
    borderRadius: 14, padding: '1rem 0.6rem',
    cursor: 'pointer', fontFamily: 'inherit',
    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.3rem',
    transition: 'all 0.3s cubic-bezier(0.34,1.2,0.64,1)',
    position: 'relative', overflow: 'hidden',
  },
  seasonActiveBg: {
    position: 'absolute', inset: 0,
    background: 'rgba(255,255,255,0.15)',
    pointerEvents: 'none',
  },
  seasonIcon:   { fontSize: '1.6rem' },
  seasonLabel:  { fontSize: '0.85rem', fontWeight: 800, transition: 'color 0.3s' },
  seasonPeriod: { fontSize: '0.65rem', transition: 'color 0.3s' },
  seasonCheck: {
    position: 'absolute', top: 6, right: 8,
    fontSize: '0.65rem', color: '#fff',
    background: 'rgba(255,255,255,0.3)',
    borderRadius: '50%', width: 16, height: 16,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontWeight: 900,
  },

  /* ADVANCED TOGGLE */
  advToggle: {
    width: '100%', background: '#f8fffe',
    border: '1.5px solid #d1fae5',
    borderRadius: 12, padding: '0.9rem 1.1rem',
    display: 'flex', alignItems: 'center',
    justifyContent: 'space-between', cursor: 'pointer',
    fontFamily: 'inherit', transition: 'all 0.25s',
  },
  advToggleLeft:  { display:'flex', alignItems:'center', gap:'0.7rem' },
  advToggleIcon:  { fontSize:'1.2rem' },
  advToggleTitle: { fontSize:'0.88rem', fontWeight:700, color:'#14532d' },
  advToggleSub:   { fontSize:'0.72rem', color:'#6b7280' },
  advChevron: {
    fontSize: '0.65rem', color: '#6b7280',
    transition: 'transform 0.3s ease',
  },
  advPanel: { marginTop: '1rem' },
  advHint: {
    background: '#f0fdf4', border: '1px solid #d1fae5',
    borderRadius: 10, padding: '0.65rem 0.9rem',
    fontSize: '0.78rem', color: '#15803d', marginBottom: '0.85rem',
  },
  advGrid: {
    display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.7rem',
  },
  advField: {
    border: '1.5px solid #e5e7eb', borderRadius: 12,
    padding: '0.75rem 0.9rem',
  },
  advLabel: {
    fontSize: '0.72rem', fontWeight: 700,
    display: 'flex', alignItems: 'center', gap: '0.3rem',
    marginBottom: '0.4rem',
  },
  advUnit: {
    background: 'rgba(255,255,255,0.7)',
    borderRadius: 4, padding: '0 0.3rem',
    fontSize: '0.6rem', fontWeight: 400,
    marginLeft: '0.2rem',
  },
  advInput: {
    width: '100%', background: 'rgba(255,255,255,0.9)',
    border: '1.5px solid', borderRadius: 8,
    padding: '0.5rem 0.75rem',
    fontSize: '0.88rem', color: '#1e293b', fontFamily: 'inherit',
    outline: 'none',
  },

  /* SUBMIT BUTTON */
  submitBtn: {
    width: '100%', padding: '1rem 1.5rem',
    background: 'linear-gradient(135deg,#16a34a,#22c55e)',
    backgroundSize: '200% 200%',
    border: 'none', borderRadius: 14,
    color: '#fff', fontFamily: 'inherit',
    fontSize: '1rem', fontWeight: 800,
    cursor: 'pointer', letterSpacing: '0.02em',
    display: 'flex', alignItems: 'center',
    justifyContent: 'center', gap: '0.7rem',
    boxShadow: '0 8px 28px rgba(22,163,74,0.4)',
    transition: 'all 0.3s ease',
    animation: 'gradShift 3s ease infinite',
  },
  submitLoading: { opacity: 0.8, cursor: 'not-allowed' },
  submitIcon:  { fontSize: '1.2rem' },
  submitArrow: { fontSize: '1rem', marginLeft: '0.2rem' },
  spinner: {
    width: 18, height: 18, border: '2.5px solid rgba(255,255,255,0.35)',
    borderTopColor: '#fff', borderRadius: '50%',
    display: 'inline-block',
    animation: 'spin 0.7s linear infinite',
  },

  /* RESULTS PANEL */
  resultsPanel: {
    background: '#fff',
    border: '1.5px solid #d1fae5',
    borderRadius: 22,
    overflow: 'hidden',
    boxShadow: '0 8px 40px rgba(22,163,74,0.1)',
  },
  resultsHeader: {
    background: 'linear-gradient(135deg,#16a34a,#22c55e,#84cc16)',
    backgroundSize: '200% 200%',
    animation: 'gradShift 4s ease infinite',
    padding: '1.6rem',
    position: 'relative', overflow: 'hidden',
  },
  resultsHeaderBg: {
    position: 'absolute', inset: 0,
    backgroundImage:
      'linear-gradient(rgba(255,255,255,0.04) 1px,transparent 1px),' +
      'linear-gradient(90deg,rgba(255,255,255,0.04) 1px,transparent 1px)',
    backgroundSize: '30px 30px',
  },
  resultsHeaderContent: {
    position: 'relative', zIndex: 1,
    display: 'flex', alignItems: 'center',
    justifyContent: 'space-between', gap: '1rem',
  },
  resultsHeaderLeft: { display: 'flex', alignItems: 'center', gap: '0.9rem' },
  resultsEmoji: {
    fontSize: '2.2rem',
    background: 'rgba(255,255,255,0.2)',
    borderRadius: '50%', width: 52, height: 52,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    flexShrink: 0,
  },
  resultsTag: {
    fontSize: '0.62rem', letterSpacing: '0.15em',
    textTransform: 'uppercase', color: 'rgba(255,255,255,0.85)',
  },
  resultsTitle: {
    fontSize: '1.3rem', fontWeight: 900, color: '#fff',
  },
  sourcePill: {
    border: '1px solid', borderRadius: 100,
    padding: '0.28rem 0.85rem',
    fontSize: '0.72rem', fontWeight: 700,
  },

  /* CONTEXT GRID */
  contextGrid: {
    display: 'grid', gridTemplateColumns: 'repeat(3,1fr)',
    gap: '0.7rem', padding: '1.2rem 1.4rem 0',
  },
  contextCard: {
    background: '#f8fafc', border: '1px solid #e2e8f0',
    borderRadius: 12, padding: '0.8rem 0.9rem',
    textAlign: 'center',
  },
  contextIcon: { fontSize: '1.2rem', display: 'block', marginBottom: '0.3rem' },
  contextVal:  { display: 'block', fontSize: '0.9rem', fontWeight: 800, color: '#14532d' },
  contextLbl:  { display: 'block', fontSize: '0.62rem', color: '#9ca3af', marginTop: '0.15rem' },
  sourceNote: {
    margin: '0.7rem 1.4rem 0',
    background: '#f0fdf4', border: '1px solid #d1fae5',
    borderRadius: 9, padding: '0.55rem 0.9rem',
    fontSize: '0.73rem', color: '#6b7280',
  },

  /* TABS */
  tabRow: {
    display: 'flex', gap: '0.6rem',
    padding: '1.1rem 1.4rem 0',
  },
  tabBtn: {
    flex: 1, padding: '0.6rem 0.5rem',
    background: '#f1f5f9', border: '1.5px solid #e2e8f0',
    borderRadius: 10, cursor: 'pointer',
    fontFamily: 'inherit', fontSize: '0.78rem', fontWeight: 700,
    color: '#475569', transition: 'all 0.3s cubic-bezier(0.34,1.2,0.64,1)',
  },

  /* REC DETAIL */
  recDetail: {
    margin: '1rem 1.4rem 0',
    border: '1px solid #e2e8f0', borderRadius: 16, overflow: 'hidden',
  },
  recHero: {
    padding: '1.4rem', position: 'relative', overflow: 'hidden',
    display: 'flex', alignItems: 'center',
    justifyContent: 'space-between', gap: '1rem',
  },
  recHeroBg: {
    position: 'absolute', inset: 0,
    background: 'rgba(0,0,0,0.08)', pointerEvents: 'none',
    backgroundImage:
      'radial-gradient(circle at 80% 50%,rgba(255,255,255,0.15) 0%,transparent 60%)',
  },
  recHeroLeft: {
    display: 'flex', alignItems: 'center', gap: '0.9rem',
    position: 'relative', zIndex: 1,
  },
  recCropEmoji: {
    fontSize: '2.8rem',
    background: 'rgba(255,255,255,0.2)',
    borderRadius: '50%', width: 60, height: 60,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    flexShrink: 0,
  },
  recMedalBadge: {
    background: 'rgba(255,255,255,0.2)',
    borderRadius: 100, padding: '0.15rem 0.7rem',
    fontSize: '0.65rem', fontWeight: 700, color: '#fff',
    letterSpacing: '0.1em', textTransform: 'uppercase',
    marginBottom: '0.3rem', display: 'inline-block',
  },
  recCropName: { fontSize: '1.5rem', fontWeight: 900, color: '#fff', lineHeight: 1 },
  recCropDesc: { fontSize: '0.8rem', color: 'rgba(255,255,255,0.82)', marginTop: '0.2rem' },

  /* CONF RING */
  ringWrap: {
    width: 72, height: 72, borderRadius: '50%',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    position: 'relative', flexShrink: 0,
    zIndex: 1,
  },
  ringLabel: {
    position: 'absolute', display: 'flex',
    alignItems: 'baseline', gap: 1,
  },
  ringNum: { fontSize: '1.05rem', fontWeight: 900, lineHeight: 1 },
  ringPct: { fontSize: '0.6rem', color: '#6b7280', fontWeight: 700 },

  /* CONF BAR */
  confBarWrap: { padding: '1rem 1.2rem' },
  confBarLabel: {
    display: 'flex', justifyContent: 'space-between',
    fontSize: '0.76rem', color: '#6b7280', marginBottom: '0.4rem',
  },
  barTrack: {
    height: 8, background: '#e2e8f0',
    borderRadius: 4, overflow: 'hidden',
  },
  barFill: { height: '100%', borderRadius: 4 },
  regionalTag: {
    margin: '0.8rem 1.2rem',
    background: '#f1f5f9', border: '1px solid #e2e8f0',
    borderRadius: 8, padding: '0.55rem 0.9rem',
    fontSize: '0.78rem', color: '#6b7280',
  },

  /* MINI CARDS */
  miniGrid: {
    display: 'grid', gridTemplateColumns: 'repeat(3,1fr)',
    gap: '0.7rem', padding: '1rem 1.4rem 0',
  },
  miniCard: {
    background: '#f8fafc',
    border: '1.5px solid #e2e8f0',
    borderTop: '3px solid',
    borderRadius: 12, padding: '0.85rem',
    textAlign: 'center',
    transition: 'all 0.25s ease',
  },
  miniTop: {
    display: 'flex', alignItems: 'center',
    justifyContent: 'center', gap: '0.3rem',
    marginBottom: '0.4rem',
  },
  miniEmoji:  { fontSize: '1.4rem' },
  miniMedal:  { fontSize: '0.9rem' },
  miniName:   { fontSize: '0.8rem', fontWeight: 700, color: '#1e293b', marginBottom: '0.2rem' },
  miniConf:   { fontSize: '0.7rem', fontWeight: 600 },

  /* DISCLAIMER */
  disclaimer: {
    margin: '1rem 1.4rem 1.4rem',
    background: '#fffbeb', border: '1px solid #fde68a',
    borderLeft: '3px solid #f59e0b', borderRadius: 10,
    padding: '0.8rem 1rem',
    display: 'flex', alignItems: 'flex-start', gap: '0.6rem',
  },
  disclaimerIcon: { fontSize: '0.95rem', flexShrink: 0, paddingTop: 1 },
  disclaimerText: {
    fontSize: '0.76rem', color: '#78350f', lineHeight: 1.65, margin: 0,
  },

  /* EMPTY STATE */
  emptyState: {
    background: '#fff', border: '2px dashed #bbf7d0',
    borderRadius: 22, padding: '3.5rem 2.5rem',
    textAlign: 'center',
    boxShadow: '0 4px 20px rgba(22,163,74,0.06)',
    position: 'relative', overflow: 'hidden',
  },
  emptyOrb: {
    position: 'absolute', top: -60, right: -60,
    width: 200, height: 200, borderRadius: '50%',
    background: 'radial-gradient(circle,rgba(134,239,172,0.2) 0%,transparent 70%)',
    pointerEvents: 'none',
  },
  emptyEmoji: { fontSize: '3.5rem', marginBottom: '0.8rem', display: 'block' },
  emptyTitle: { fontSize: '1.15rem', fontWeight: 800, color: '#14532d', marginBottom: '0.4rem' },
  emptySub:   { color: '#6b7280', fontSize: '0.85rem', lineHeight: 1.65, maxWidth: 360, margin: '0 auto 1.8rem' },
  emptySteps: { display:'flex', justifyContent:'center', gap:'0.8rem', flexWrap:'wrap' },
  emptyStep:  {
    display: 'flex', alignItems: 'center', gap: '0.5rem',
    background: '#f0fdf4', border: '1px solid #d1fae5',
    borderRadius: 100, padding: '0.38rem 0.9rem',
  },
  emptyStepNum: {
    width: 20, height: 20, borderRadius: '50%',
    background: 'linear-gradient(135deg,#16a34a,#22c55e)',
    color: '#fff', fontSize: '0.62rem', fontWeight: 900,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  emptyStepLabel: { fontSize: '0.75rem', fontWeight: 600, color: '#15803d' },

  /* LOADING STATE */
  loadingState: {
    background: '#fff', border: '1.5px solid #d1fae5',
    borderRadius: 22, padding: '3rem 2rem',
    textAlign: 'center',
    boxShadow: '0 4px 24px rgba(22,163,74,0.08)',
  },
  loadingRing: {
    width: 80, height: 80, borderRadius: '50%',
    margin: '0 auto 1.2rem',
    background: 'linear-gradient(135deg,#dcfce7,#bbf7d0)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    position: 'relative',
  },
  loadingInnerRing: {
    position: 'absolute', inset: 4,
    borderRadius: '50%', border: '3px solid transparent',
    borderTopColor: '#16a34a',
    animation: 'spin 1s linear infinite',
  },
  loadingEmoji:  { fontSize: '2rem', position: 'relative', zIndex: 1 },
  loadingTitle:  { fontSize: '1rem', fontWeight: 800, color: '#14532d', marginBottom: '1.2rem' },
  loadingSteps:  { display: 'flex', flexDirection: 'column', gap: '0.5rem', maxWidth: 240, margin: '0 auto' },
  loadingStep: {
    display: 'flex', alignItems: 'center', gap: '0.6rem',
    fontSize: '0.8rem', color: '#6b7280',
    animation: 'pulse 1.4s ease infinite',
  },
  loadingDot: {
    width: 7, height: 7, borderRadius: '50%',
    background: '#22c55e', flexShrink: 0,
    animation: 'pulse 1.2s ease infinite',
  },

  /* RESPONSIVE hint — add media queries via inline or CSS file if needed */
  inputPanel: {},
};