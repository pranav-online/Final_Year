import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { getWeatherAdvisory } from '../services/api';
import toast from 'react-hot-toast';

/* ---------- scene themes: the whole page re-tints to the live weather ---------- */
const SCENES = {
  idle:  { sky: ['#14284b', '#2f5d8a', '#e8a76a'], ink: '#fff', label: 'Waiting for a location' },
  clear: { sky: ['#1769b3', '#5bb6e6', '#ffe3a1'], ink: '#fff', label: 'Clear skies' },
  cloud: { sky: ['#3d5572', '#7f97b0', '#cfd9e3'], ink: '#fff', label: 'Cloud cover' },
  rain:  { sky: ['#1d2f46', '#3a5875', '#6f8da6'], ink: '#fff', label: 'Rain' },
  storm: { sky: ['#0f1624', '#252f48', '#4a4f6e'], ink: '#fff', label: 'Storm' },
  mist:  { sky: ['#5b6b72', '#93a3a8', '#d5dcd9'], ink: '#fff', label: 'Mist' }
};

function sceneFor(w) {
  if (!w) return 'idle';
  const c = String(w.condition || '').toLowerCase();
  if (/thunder|storm/.test(c)) return 'storm';
  if (/rain|drizzle|shower/.test(c) || Number(w.rainfall) > 1) return 'rain';
  if (/mist|fog|haze|smoke/.test(c)) return 'mist';
  if (/cloud|overcast/.test(c)) return 'cloud';
  return 'clear';
}

const SEVERITY = {
  high:   { color: '#ff6b5a', label: 'High' },
  medium: { color: '#ffb84a', label: 'Medium' },
  low:    { color: '#5ee0a0', label: 'Low' }
};

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

/* ---------- sky layer ---------- */
function Sky({ scene, rainfall = 0, wind = 0 }) {
  const drops = useMemo(() => {
    const n = scene === 'storm' ? 70 : scene === 'rain' ? Math.min(30 + Math.round(rainfall * 3), 70) : 0;
    return Array.from({ length: n }, (_, i) => ({
      left: Math.random() * 100,
      delay: Math.random() * 2,
      dur: 0.55 + Math.random() * 0.5,
      h: 14 + Math.random() * 14,
      key: i
    }));
  }, [scene, rainfall]);

  const streaks = useMemo(
    () => Array.from({ length: 6 }, (_, i) => ({ top: 12 + i * 13, delay: i * 0.7, key: i })),
    []
  );
  const windDur = Math.max(1.4, 7 - wind / 5);
  const showSun = scene === 'clear' || scene === 'idle';
  const clouds = scene === 'clear' ? 2 : scene === 'idle' ? 1 : 4;

  return (
    <div className="wa-sky" aria-hidden="true">
      {showSun && (
        <div className={`wa-sun ${scene === 'idle' ? 'wa-sun-low' : ''}`}>
          <div className="wa-rays" />
          <div className="wa-sun-core" />
        </div>
      )}
      {Array.from({ length: clouds }).map((_, i) => (
        <div
          key={i}
          className="wa-cloud"
          style={{
            top: `${8 + i * 16}%`,
            animationDuration: `${60 + i * 25}s`,
            animationDelay: `${-i * 18}s`,
            transform: `scale(${1 + (i % 2) * 0.5})`,
            opacity: scene === 'storm' ? 0.85 : 0.55
          }}
        />
      ))}
      {drops.map((d) => (
        <span
          key={d.key}
          className="wa-drop"
          style={{ left: `${d.left}%`, height: d.h, animationDelay: `${d.delay}s`, animationDuration: `${d.dur}s` }}
        />
      ))}
      {scene === 'storm' && <div className="wa-flash" />}
      {wind > 12 &&
        streaks.map((s) => (
          <span
            key={s.key}
            className="wa-streak"
            style={{ top: `${s.top}%`, animationDelay: `${s.delay}s`, animationDuration: `${windDur}s` }}
          />
        ))}
      <div className="wa-hills">
        <svg viewBox="0 0 1200 160" preserveAspectRatio="none">
          <path d="M0 90 C 200 30, 380 140, 600 80 S 1000 20, 1200 90 V160 H0Z" fill="#14402b" opacity=".55" />
          <path d="M0 120 C 250 70, 450 150, 700 110 S 1050 70, 1200 120 V160 H0Z" fill="#0f3322" />
        </svg>
      </div>
    </div>
  );
}

/* ---------- gauges ---------- */
function RingGauge({ icon, label, value, pct, unit, ready, delay }) {
  const C = 2 * Math.PI * 44;
  return (
    <div className="wa-gauge" style={{ animationDelay: `${delay}ms` }}>
      <svg viewBox="0 0 100 100" className="wa-ring">
        <circle cx="50" cy="50" r="44" className="wa-ring-bg" />
        <circle
          cx="50" cy="50" r="44" className="wa-ring-fg"
          strokeDasharray={C}
          strokeDashoffset={ready ? C * (1 - Math.min(pct, 100) / 100) : C}
        />
      </svg>
      <div className="wa-gauge-in">
        <span className="wa-gauge-icon">{icon}</span>
        <strong>{value}<small>{unit}</small></strong>
      </div>
      <p>{label}</p>
    </div>
  );
}

function WindGauge({ speed, delay }) {
  const dur = Math.max(0.5, 5 - speed / 6);
  return (
    <div className="wa-gauge" style={{ animationDelay: `${delay}ms` }}>
      <svg viewBox="0 0 100 100" className="wa-ring">
        <circle cx="50" cy="50" r="44" className="wa-ring-bg" />
        <g className="wa-pin" style={{ animationDuration: `${dur}s` }}>
          {[0, 90, 180, 270].map((a) => (
            <path key={a} d="M50 50 L50 20 Q70 24 62 42 Z" fill="#bfe9ff" opacity=".9" transform={`rotate(${a} 50 50)`} />
          ))}
        </g>
        <circle cx="50" cy="50" r="4" fill="#fff" />
      </svg>
      <div className="wa-gauge-in wa-gauge-low"><strong>{speed.toFixed(1)}<small> km/h</small></strong></div>
      <p>Wind speed</p>
    </div>
  );
}

function RainGauge({ mm, ready, delay }) {
  const pct = Math.min(mm / 50, 1) * 100;
  return (
    <div className="wa-gauge" style={{ animationDelay: `${delay}ms` }}>
      <div className="wa-tube">
        <div className="wa-tube-fill" style={{ height: ready ? `${Math.max(pct, mm > 0 ? 8 : 3)}%` : '0%' }} />
        {[25, 50, 75].map((t) => <i key={t} style={{ bottom: `${t}%` }} />)}
      </div>
      <div className="wa-gauge-in wa-gauge-low"><strong>{mm}<small> mm</small></strong></div>
      <p>Rainfall</p>
    </div>
  );
}

/* ---------- page ---------- */
export default function WeatherAdvisory() {
  const navigate = useNavigate();
  const [location, setLocation] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);

  const w = result?.weather;
  const sceneKey = sceneFor(w);
  const scene = SCENES[sceneKey];
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
      const res = await getWeatherAdvisory(location);
      setResult(res.data);
      toast.success('Weather data loaded!');
    } catch (err) {
      toast.error('Location not found. Try another city!');
    }
    setLoading(false);
  };

  return (
    <div className="wa-root">
      <style>{CSS}</style>

      <section
        className="wa-hero"
        style={{ background: `linear-gradient(180deg, ${scene.sky[0]} 0%, ${scene.sky[1]} 55%, ${scene.sky[2]} 100%)` }}
      >
        <Sky scene={sceneKey} rainfall={Number(w?.rainfall) || 0} wind={Number(w?.wind_speed) || 0} />

        <button className="wa-back" onClick={() => navigate('/farmer')}>← Back</button>

        <div className="wa-hero-body">
          {w ? (
            <div className="wa-reading" key={w.location + w.temperature}>
              <p className="wa-place">{w.location}</p>
              <h1 className="wa-temp">{Math.round(temp)}<sup>°C</sup></h1>
              <p className="wa-cond">{w.condition}</p>
            </div>
          ) : (
            <div className="wa-reading">
              <h1 className="wa-ask">Where are you farming today?</h1>
              <p className="wa-cond">Get a weather read and what it means for your crops.</p>
            </div>
          )}

          <div className="wa-search">
            <input
              value={location}
              placeholder="Hyderabad, Chennai, Mumbai…"
              onChange={(e) => setLocation(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
              aria-label="Location"
            />
            <button onClick={handleSubmit} disabled={loading}>
              {loading ? (
                <span className="wa-sprout" aria-label="Loading"><i /><i /><i /></span>
              ) : (
                'Get advisory'
              )}
            </button>
          </div>
        </div>
      </section>

      {result && (
        <main className="wa-main" key={w.location + w.temperature}>
          <div className="wa-gauges">
            <RingGauge icon="💧" label="Humidity" value={Math.round(w.humidity)} unit="%" pct={w.humidity} ready={ready} delay={0} />
            <WindGauge speed={Number(w.wind_speed) || 0} delay={120} />
            <RainGauge mm={Number(w.rainfall) || 0} ready={ready} delay={240} />
          </div>

          <h2 className="wa-h2">
            What to do on the farm <span>{result.total_advisories}</span>
          </h2>

          <div className="wa-list">
            {result.advisories.map((adv, idx) => {
              const isStr = typeof adv === 'string';
              const sev = SEVERITY[String(adv.severity || 'low').toLowerCase()] || SEVERITY.low;
              return (
                <article
                  key={idx}
                  className="wa-adv"
                  style={{ '--sev': isStr ? '#5ee0a0' : sev.color, animationDelay: `${360 + idx * 110}ms` }}
                >
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
                </article>
              );
            })}
          </div>
        </main>
      )}
    </div>
  );
}

/* ---------- styles ---------- */
const CSS = `
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=DM+Sans:wght@400;500;700&display=swap');

.wa-root { min-height:100vh; background:#0c1a14; color:#e9f3ee; font-family:'DM Sans',system-ui,sans-serif; }
.wa-root * { box-sizing:border-box; }

/* hero */
.wa-hero { position:relative; overflow:hidden; min-height:540px; transition:background 1s ease; }
.wa-sky { position:absolute; inset:0; pointer-events:none; }
.wa-back { position:absolute; z-index:5; top:20px; left:24px; padding:8px 16px; border-radius:999px; border:1px solid rgba(255,255,255,.35);
  background:rgba(255,255,255,.14); color:#fff; font:500 14px 'DM Sans'; cursor:pointer; backdrop-filter:blur(8px); }
.wa-back:hover { background:rgba(255,255,255,.26); }
.wa-back:focus-visible, .wa-search input:focus-visible, .wa-search button:focus-visible { outline:3px solid #fff; outline-offset:2px; }
.wa-hero-body { position:relative; z-index:4; min-height:540px; padding:90px 32px 48px; display:flex; flex-direction:column; justify-content:flex-end; gap:28px; max-width:900px; margin:0 auto; }
.wa-reading { animation:wa-rise .9s cubic-bezier(.2,.8,.2,1) both; }
.wa-place { margin:0; font:500 18px 'DM Sans'; opacity:.9; }
.wa-temp { margin:0; font:800 clamp(96px,22vw,200px)/0.9 'Bricolage Grotesque',sans-serif; letter-spacing:-.04em; text-shadow:0 8px 40px rgba(0,0,0,.25); }
.wa-temp sup { font-size:.32em; font-weight:500; vertical-align:top; margin-left:6px; position:relative; top:.35em; }
.wa-ask { margin:0 0 10px; font:800 clamp(34px,6vw,60px)/1.05 'Bricolage Grotesque',sans-serif; letter-spacing:-.02em; max-width:12em; }
.wa-cond { margin:6px 0 0; font:500 20px 'DM Sans'; opacity:.92; max-width:30em; }

/* search */
.wa-search { display:flex; gap:8px; padding:6px; border-radius:999px; background:rgba(255,255,255,.2); border:1px solid rgba(255,255,255,.4); backdrop-filter:blur(14px); }
.wa-search input { flex:1; min-width:0; padding:12px 20px; border:0; background:transparent; color:#fff; font:500 16px 'DM Sans'; outline:none; }
.wa-search input::placeholder { color:rgba(255,255,255,.7); }
.wa-search button { min-width:140px; padding:12px 24px; border:0; border-radius:999px; background:#fff; color:#12351f; font:700 15px 'DM Sans'; cursor:pointer; transition:transform .2s; }
.wa-search button:hover:not(:disabled) { transform:scale(1.04); }
.wa-search button:disabled { cursor:progress; }
.wa-sprout { display:inline-flex; align-items:flex-end; gap:5px; height:18px; }
.wa-sprout i { width:5px; height:100%; background:#2d8a4f; border-radius:3px; transform-origin:bottom; animation:wa-grow 1s ease-in-out infinite; }
.wa-sprout i:nth-child(2) { animation-delay:.15s; } .wa-sprout i:nth-child(3) { animation-delay:.3s; }

/* sky elements */
.wa-sun { position:absolute; top:70px; right:12%; width:150px; height:150px; animation:wa-bob 8s ease-in-out infinite; }
.wa-sun-low { top:auto; bottom:90px; right:18%; }
.wa-sun-core { position:absolute; inset:30px; border-radius:50%; background:radial-gradient(circle at 35% 35%,#fff7cf,#ffd76a 60%,#ffb82e); box-shadow:0 0 60px 20px rgba(255,214,102,.6); }
.wa-rays { position:absolute; inset:-30px; border-radius:50%; animation:wa-spin 30s linear infinite;
  background:repeating-conic-gradient(from 0deg, rgba(255,235,160,.5) 0 4deg, transparent 4deg 20deg);
  -webkit-mask:radial-gradient(circle,transparent 38%,#000 40%,transparent 72%); mask:radial-gradient(circle,transparent 38%,#000 40%,transparent 72%); }
.wa-cloud { position:absolute; left:-300px; width:220px; height:60px; border-radius:60px; background:#fff; filter:blur(1px); animation:wa-drift linear infinite; }
.wa-cloud::before, .wa-cloud::after { content:''; position:absolute; background:#fff; border-radius:50%; }
.wa-cloud::before { width:90px; height:90px; top:-45px; left:35px; }
.wa-cloud::after { width:70px; height:70px; top:-30px; left:110px; }
.wa-drop { position:absolute; top:-40px; width:2px; border-radius:2px; background:linear-gradient(transparent,rgba(190,225,255,.85)); animation:wa-fall linear infinite; }
.wa-flash { position:absolute; inset:0; background:#dfe7ff; opacity:0; animation:wa-flash 7s infinite; }
.wa-streak { position:absolute; left:-30%; width:30%; height:2px; border-radius:2px; background:linear-gradient(90deg,transparent,rgba(255,255,255,.7),transparent); animation:wa-wind linear infinite; }
.wa-hills { position:absolute; left:0; right:0; bottom:-1px; height:110px; }
.wa-hills svg { width:100%; height:100%; display:block; }

/* main */
.wa-main { max-width:900px; margin:0 auto; padding:36px 24px 72px; }
.wa-gauges { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; }
.wa-gauge { position:relative; text-align:center; padding:18px 8px 14px; border-radius:20px; background:#12261c; border:1px solid #1f3c2d; animation:wa-rise .7s cubic-bezier(.2,.8,.2,1) both; }
.wa-gauge p { margin:8px 0 0; font:500 13px 'DM Sans'; color:#9dbcab; }
.wa-ring { width:104px; height:104px; display:block; margin:0 auto; }
.wa-ring-bg { fill:none; stroke:#1f3c2d; stroke-width:8; }
.wa-ring-fg { fill:none; stroke:#5bc0f8; stroke-width:8; stroke-linecap:round; transform:rotate(-90deg); transform-origin:50% 50%; transition:stroke-dashoffset 1.6s cubic-bezier(.2,.8,.2,1) .2s; }
.wa-gauge-in { position:absolute; top:18px; left:0; right:0; height:104px; display:flex; flex-direction:column; align-items:center; justify-content:center; }
.wa-gauge-low { justify-content:flex-end; padding-bottom:6px; }
.wa-gauge-icon { font-size:18px; }
.wa-gauge-in strong { font:800 24px 'Bricolage Grotesque',sans-serif; }
.wa-gauge-in small { font:500 12px 'DM Sans'; color:#9dbcab; }
.wa-pin { transform-origin:50px 50px; animation:wa-spin linear infinite; }
.wa-tube { position:relative; width:46px; height:104px; margin:0 auto; border-radius:23px; border:2px solid #2c5640; overflow:hidden; background:#0d1d15; }
.wa-tube-fill { position:absolute; left:0; right:0; bottom:0; background:linear-gradient(180deg,#8fd6ff,#2b8fe0); transition:height 1.8s cubic-bezier(.2,.8,.2,1) .3s; }
.wa-tube-fill::before { content:''; position:absolute; top:-5px; left:0; right:0; height:10px; border-radius:50%; background:#aee2ff; animation:wa-bob 2.4s ease-in-out infinite; }
.wa-tube i { position:absolute; right:0; width:12px; height:2px; background:rgba(255,255,255,.35); }

.wa-h2 { display:flex; align-items:center; gap:12px; margin:44px 0 16px; font:800 28px 'Bricolage Grotesque',sans-serif; letter-spacing:-.01em; }
.wa-h2 span { padding:2px 12px; border-radius:999px; background:#1c3a2a; color:#7ee2a8; font:700 16px 'DM Sans'; }
.wa-list { display:flex; flex-direction:column; gap:12px; }
.wa-adv { position:relative; padding:16px 20px 16px 24px; border-radius:14px; background:#12261c; border:1px solid #1f3c2d; overflow:hidden; animation:wa-rise .7s cubic-bezier(.2,.8,.2,1) both; }
.wa-adv::before { content:''; position:absolute; left:0; top:0; bottom:0; width:5px; background:var(--sev); box-shadow:0 0 18px var(--sev); }
.wa-adv-text { margin:0; font:500 16px/1.55 'DM Sans'; max-width:62ch; }
.wa-adv-meta { display:flex; align-items:center; flex-wrap:wrap; gap:12px; margin-top:10px; font-size:13px; color:#9dbcab; }
.wa-adv-meta b { color:var(--sev); font-weight:700; }
.wa-bar { width:110px; height:6px; border-radius:3px; background:#1f3c2d; overflow:hidden; }
.wa-bar div { height:100%; border-radius:3px; background:var(--sev); transition:width 1.4s cubic-bezier(.2,.8,.2,1) .5s; }

/* keyframes */
@keyframes wa-spin  { to { transform:rotate(360deg); } }
@keyframes wa-drift { to { transform:translateX(calc(100vw + 600px)); } }
@keyframes wa-fall  { to { transform:translateY(640px); } }
@keyframes wa-wind  { to { transform:translateX(480%); } }
@keyframes wa-bob   { 50% { transform:translateY(-8px); } }
@keyframes wa-flash { 0%,90%,100% { opacity:0; } 92% { opacity:.55; } 94% { opacity:.05; } 96% { opacity:.4; } }
@keyframes wa-grow  { 0%,100% { transform:scaleY(.3); } 50% { transform:scaleY(1); } }
@keyframes wa-rise  { from { opacity:0; transform:translateY(22px); } to { opacity:1; transform:none; } }

@media (max-width:600px) {
  .wa-hero-body { padding:80px 20px 40px; }
  .wa-gauges { gap:10px; }
  .wa-ring { width:84px; height:84px; }
  .wa-gauge-in { height:84px; }
  .wa-tube { height:84px; }
}
@media (prefers-reduced-motion: reduce) {
  .wa-root *, .wa-root *::before { animation-duration:.01ms !important; animation-iteration-count:1 !important; transition-duration:.01ms !important; }
}
`;