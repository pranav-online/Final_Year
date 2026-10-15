import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

/* ═══════════════════════════════════════════════════════════════
   ALIP — Farmer Dashboard  ·  Professional Light Mode
   Same design language as the Broker Dashboard:
   · Glassmorphism sticky header with live clock
   · Floating orb background + hero with grid lines
   · Staggered card entrance, ripple + shimmer on hover
   · Time-of-day greeting and rotating farming tips
═══════════════════════════════════════════════════════════════ */

const MODULES = [
  {
    icon: '🌱',
    title: 'Crop Recommendation',
    desc: 'Get the best crop suggestion for your region and soil',
    path: '/crop',
    grad: 'linear-gradient(135deg,#16a34a,#4ade80)',
    glow: 'rgba(22,163,74,0.28)',
    tag: 'Planning',
  },
  {
    icon: '🔬',
    title: 'Disease Detection',
    desc: 'Upload a leaf image to detect crop disease early',
    path: '/disease',
    grad: 'linear-gradient(135deg,#dc2626,#f87171)',
    glow: 'rgba(220,38,38,0.28)',
    tag: 'AI Scan',
  },
  {
    icon: '🌦️',
    title: 'Weather Advisory',
    desc: 'Real-time weather with farming advice for your fields',
    path: '/weather',
    grad: 'linear-gradient(135deg,#0284c7,#38bdf8)',
    glow: 'rgba(2,132,199,0.28)',
    tag: 'Forecast',
  },
  {
    icon: '📦',
    title: 'Add Crop Listing',
    desc: 'List your crop for market sale with price and quantity',
    path: '/listing',
    grad: 'linear-gradient(135deg,#ea580c,#fb923c)',
    glow: 'rgba(234,88,12,0.28)',
    tag: 'Sell',
  },
];

const TIPS = [
  'Scout your leaves early in the morning — disease spots are easiest to see in soft light.',
  'Check the forecast before irrigating. Skipping one watering before rain saves water and money.',
  'Rotate crops each season to keep soil nutrients balanced and reduce pests.',
  'List your crop a few weeks before harvest so brokers can plan their purchases.',
];

/* ── Live clock ── */
function useClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const iv = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(iv);
  }, []);
  return now;
}

/* ── Ripple effect ── */
function useRipple() {
  const [ripple, setRipple] = useState(null);
  const trigger = (e, el) => {
    const rect = el.getBoundingClientRect();
    setRipple({ x: e.clientX - rect.left, y: e.clientY - rect.top, key: Date.now() });
    setTimeout(() => setRipple(null), 700);
  };
  return [ripple, trigger];
}

const firstColor = (grad, fallback) => grad.match(/#[0-9a-f]{6}/i)?.[0] || fallback;

/* ── Module card ── */
function ModuleCard({ mod, idx, onClick }) {
  const [hovered, setHovered] = useState(false);
  const [ripple, triggerRipple] = useRipple();
  const ref = useRef(null);
  const accent = firstColor(mod.grad, '#333');

  const handleClick = (e) => {
    triggerRipple(e, ref.current);
    setTimeout(() => onClick(mod.path), 180);
  };

  return (
    <div
      ref={ref}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick(mod.path)}
      style={{
        ...S.card,
        animationDelay: `${0.08 + idx * 0.09}s`,
        transform: hovered ? 'translateY(-8px) scale(1.02)' : 'translateY(0) scale(1)',
        boxShadow: hovered
          ? `0 24px 48px ${mod.glow}, 0 0 0 1px rgba(0,0,0,0.04)`
          : '0 4px 24px rgba(0,0,0,0.07)',
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={handleClick}
    >
      {/* Shimmer */}
      <div
        style={{
          ...S.cardShimmer,
          opacity: hovered ? 1 : 0,
          background: `linear-gradient(105deg,transparent 40%,${mod.glow.replace('0.28', '0.12')} 50%,transparent 60%)`,
          animation: hovered ? 'shimmer 1.4s ease infinite' : 'none',
        }}
      />

      {/* Ripple */}
      {ripple && (
        <span
          key={ripple.key}
          style={{
            ...S.ripple,
            left: ripple.x,
            top: ripple.y,
            background: mod.glow.replace('0.28', '0.35'),
          }}
        />
      )}

      <div style={{ ...S.cardTag, background: mod.glow.replace('0.28', '0.1'), color: accent }}>
        {mod.tag}
      </div>

      <div style={{ ...S.cardIconWrap, background: mod.grad, boxShadow: `0 8px 20px ${mod.glow}` }}>
        <span style={S.cardIconEmoji}>{mod.icon}</span>
        <div style={{ ...S.iconRing, borderColor: mod.glow.replace('0.28', '0.5'), opacity: hovered ? 1 : 0 }} />
      </div>

      <h3 style={S.cardTitle}>{mod.title}</h3>
      <p style={S.cardDesc}>{mod.desc}</p>

      <div
        style={{
          ...S.cardBtn,
          background: hovered ? mod.grad : 'transparent',
          color: hovered ? '#fff' : accent,
          borderColor: accent,
        }}
      >
        Open Module →
      </div>
    </div>
  );
}

/* ── Main component ── */
export default function FarmerDashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const now = useClock();
  const [scrolled, setScrolled] = useState(false);
  const [tipIdx, setTipIdx] = useState(0);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    const iv = setInterval(() => setTipIdx((i) => (i + 1) % TIPS.length), 8000);
    return () => clearInterval(iv);
  }, []);

  const handleLogout = () => {
    logout();
    toast.success('Logged out successfully!');
    navigate('/login');
  };

  const hour = now.getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  const time = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  const dateStr = now.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' });
  const name = user?.full_name || 'Farmer';

  return (
    <div style={S.page}>
      <style>{KEYFRAMES}</style>

      {/* Floating orbs */}
      <div style={S.orb1} />
      <div style={S.orb2} />
      <div style={S.orb3} />

      {/* ═══ HEADER ═══ */}
      <header
        style={{
          ...S.header,
          background: scrolled ? 'rgba(255,255,255,0.92)' : 'rgba(255,255,255,0.75)',
          boxShadow: scrolled ? '0 4px 30px rgba(0,0,0,0.10)' : '0 1px 0 rgba(0,0,0,0.06)',
          backdropFilter: 'blur(20px)',
        }}
      >
        <div style={S.headerInner}>
          <div style={S.logoWrap}>
            <div style={S.logoBadge}>
              <span style={S.logoLeaf}>🌿</span>
            </div>
            <div>
              <div style={S.logoText}>
                ALIP<span style={S.logoDot}>.</span>
              </div>
              <div style={S.logoSub}>Farmer Dashboard</div>
            </div>
          </div>

          <nav style={S.nav}>
            {[
              { label: 'Dashboard', path: null },
              { label: 'Crops', path: '/crop' },
              { label: 'Weather', path: '/weather' },
              { label: 'Listings', path: '/listing' },
            ].map((item, i) => (
              <button
                key={item.label}
                style={{ ...S.navPill, ...(i === 0 ? S.navPillActive : {}) }}
                onClick={() => item.path && navigate(item.path)}
              >
                {item.label}
              </button>
            ))}
          </nav>

          <div style={S.headerRight}>
            <div style={S.clockWrap}>
              <span style={S.clockDot} />
              <span style={S.clockTime}>{time}</span>
            </div>

            <div style={S.avatarWrap}>
              <div style={S.avatar}>{name[0]?.toUpperCase()}</div>
              <div style={S.avatarInfo}>
                <div style={S.avatarName}>{name}</div>
                <div style={S.avatarRole}>👨‍🌾 Farmer</div>
              </div>
            </div>

            <button style={S.profileBtn} onClick={() => navigate('/profile')}>
              👤 Profile
            </button>
            <button style={S.logoutBtn} onClick={handleLogout}>
              🚪 Logout
            </button>
          </div>
        </div>
      </header>

      {/* ═══ HERO ═══ */}
      <section style={S.hero}>
        <div style={S.heroContent}>
          <div style={S.heroLeft}>
            <div style={S.heroBadge}>
              <span style={S.heroBadgeDot} /> Farm Intelligence Active
            </div>
            <h1 style={S.heroTitle}>
              {greeting},<br />
              <span style={S.heroTitleGrad}>{name}</span>
            </h1>
            <p style={S.heroSub}>
              Get crop advice, check your fields for disease, plan around the weather and sell your
              harvest — all from one place.
            </p>
            <button style={S.heroBtn} onClick={() => navigate('/crop')}>
              Get Crop Recommendation →
            </button>
          </div>

          {/* Today panel */}
          <div style={S.todayCard}>
            <div style={S.todayTop}>
              <div>
                <div style={S.todayLabel}>Today</div>
                <div style={S.todayDate}>{dateStr}</div>
              </div>
              <div style={S.todayTime}>{time}</div>
            </div>
            <div style={S.todayDivider} />
            <div style={S.tipHead}>
              <span style={S.tipIcon}>💡</span> Farming tip
            </div>
            <p key={tipIdx} style={S.tipText}>
              {TIPS[tipIdx]}
            </p>
            <div style={S.tipDots}>
              {TIPS.map((_, i) => (
                <span
                  key={i}
                  style={{ ...S.tipDot, background: i === tipIdx ? '#16a34a' : '#d1d5db', width: i === tipIdx ? 18 : 6 }}
                />
              ))}
            </div>
          </div>
        </div>
        <div style={S.heroGrid} />
      </section>

      {/* ═══ MODULES ═══ */}
      <section style={S.modulesSection}>
        <div style={S.sectionHeader}>
          <div>
            <div style={S.sectionTag}>
              <span style={S.sectionTagDot} />
              Farmer Modules
            </div>
            <h2 style={S.sectionTitle}>What would you like to do today?</h2>
          </div>
          <p style={S.sectionSub}>Pick a tool to get started. Everything is tuned to your region.</p>
        </div>

        <div style={S.cardsGrid}>
          {MODULES.map((mod, idx) => (
            <ModuleCard key={mod.path} mod={mod} idx={idx} onClick={navigate} />
          ))}
        </div>
      </section>

      {/* ═══ FOOTER ═══ */}
      <footer style={S.footer}>
        <div style={S.footerInner}>
          <span style={S.footerLogo}>
            ALIP<span style={S.logoDot}>.</span>
          </span>
          <span style={S.footerCopy}>© {now.getFullYear()} AgriLink Intelligence Platform · Farmer Module</span>
          <div style={S.footerLinks}>
            {['Home', 'AI Engine', 'Supplements', 'Contact'].map((l) => (
              <span key={l} style={S.footerLink}>{l}</span>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   STYLES
═══════════════════════════════════════════════════════════════ */
const S = {
  page: {
    minHeight: '100vh',
    background: 'linear-gradient(160deg,#f0fdf4 0%,#f8fafc 50%,#f0f4ff 100%)',
    fontFamily: "'Segoe UI','Outfit',sans-serif",
    color: '#1e293b',
    overflowX: 'hidden',
    position: 'relative',
  },

  /* ORBS */
  orb1: {
    position: 'fixed', top: -120, left: -80, width: 400, height: 400,
    borderRadius: '50%', pointerEvents: 'none', zIndex: 0,
    background: 'radial-gradient(circle,rgba(134,239,172,0.18) 0%,transparent 70%)',
    animation: 'orbFloat1 12s ease-in-out infinite',
  },
  orb2: {
    position: 'fixed', top: '30%', right: -100, width: 350, height: 350,
    borderRadius: '50%', pointerEvents: 'none', zIndex: 0,
    background: 'radial-gradient(circle,rgba(147,197,253,0.15) 0%,transparent 70%)',
    animation: 'orbFloat2 15s ease-in-out infinite',
  },
  orb3: {
    position: 'fixed', bottom: -80, left: '35%', width: 300, height: 300,
    borderRadius: '50%', pointerEvents: 'none', zIndex: 0,
    background: 'radial-gradient(circle,rgba(253,224,71,0.12) 0%,transparent 70%)',
    animation: 'orbFloat3 18s ease-in-out infinite',
  },

  /* HEADER */
  header: {
    position: 'sticky', top: 0, zIndex: 100,
    borderBottom: '1px solid rgba(0,0,0,0.06)',
    transition: 'all 0.35s ease',
  },
  headerInner: {
    maxWidth: 1280, margin: '0 auto', padding: '0.85rem 2rem',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem',
  },
  logoWrap: { display: 'flex', alignItems: 'center', gap: '0.7rem', flexShrink: 0 },
  logoBadge: {
    width: 36, height: 36, borderRadius: 10,
    background: 'linear-gradient(135deg,#16a34a,#4ade80)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 4px 12px rgba(22,163,74,0.35)',
  },
  logoLeaf: { fontSize: '1.1rem' },
  logoText: { fontFamily: "'Georgia',serif", fontSize: '1.3rem', fontWeight: 900, color: '#14532d', letterSpacing: '0.07em' },
  logoDot: { color: '#84cc16' },
  logoSub: { fontSize: '0.65rem', color: '#6b7280', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase' },

  nav: { display: 'flex', gap: '0.3rem', flex: 1, justifyContent: 'center' },
  navPill: {
    padding: '0.4rem 1rem', borderRadius: 100, border: '1px solid transparent',
    background: 'transparent', color: '#6b7280', fontSize: '0.82rem', fontWeight: 600,
    cursor: 'pointer', fontFamily: 'inherit', transition: 'all 0.2s',
  },
  navPillActive: { background: '#f0fdf4', borderColor: '#bbf7d0', color: '#15803d' },

  headerRight: { display: 'flex', alignItems: 'center', gap: '0.8rem', flexShrink: 0 },
  clockWrap: {
    display: 'flex', alignItems: 'center', gap: '0.4rem',
    background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 100, padding: '0.3rem 0.9rem',
  },
  clockDot: {
    width: 7, height: 7, borderRadius: '50%', background: '#22c55e',
    display: 'inline-block', animation: 'pulse 2s ease infinite',
  },
  clockTime: { fontSize: '0.78rem', fontWeight: 700, color: '#374151', fontFamily: 'monospace' },

  avatarWrap: { display: 'flex', alignItems: 'center', gap: '0.5rem' },
  avatar: {
    width: 36, height: 36, borderRadius: '50%',
    background: 'linear-gradient(135deg,#16a34a,#22c55e)',
    color: '#fff', fontSize: '0.9rem', fontWeight: 800,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 3px 10px rgba(22,163,74,0.35)',
  },
  avatarInfo: {},
  avatarName: { fontSize: '0.8rem', fontWeight: 700, color: '#1e293b' },
  avatarRole: { fontSize: '0.65rem', color: '#6b7280' },

  profileBtn: {
    padding: '0.42rem 1rem', background: '#f0fdf4', border: '1.5px solid #bbf7d0',
    borderRadius: 100, color: '#15803d', fontSize: '0.78rem', fontWeight: 700,
    cursor: 'pointer', fontFamily: 'inherit',
  },
  logoutBtn: {
    padding: '0.42rem 1rem', background: '#fff1f2', border: '1.5px solid #fecdd3',
    borderRadius: 100, color: '#dc2626', fontSize: '0.78rem', fontWeight: 700,
    cursor: 'pointer', fontFamily: 'inherit',
  },

  /* HERO */
  hero: {
    position: 'relative', overflow: 'hidden', zIndex: 1,
    padding: '4rem 2rem 3rem',
    background: 'linear-gradient(135deg,rgba(240,253,244,0.8) 0%,rgba(240,244,255,0.9) 100%)',
    borderBottom: '1px solid #e2e8f0',
  },
  heroGrid: {
    position: 'absolute', inset: 0, pointerEvents: 'none',
    backgroundImage:
      'linear-gradient(rgba(22,163,74,0.04) 1px,transparent 1px),' +
      'linear-gradient(90deg,rgba(22,163,74,0.04) 1px,transparent 1px)',
    backgroundSize: '50px 50px',
  },
  heroContent: {
    maxWidth: 1280, margin: '0 auto',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    gap: '3rem', flexWrap: 'wrap', position: 'relative', zIndex: 1,
  },
  heroLeft: { maxWidth: 520 },
  heroBadge: {
    display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
    background: 'rgba(22,163,74,0.08)', border: '1px solid #bbf7d0',
    borderRadius: 100, padding: '0.35rem 1rem',
    fontSize: '0.72rem', fontWeight: 700, color: '#15803d',
    marginBottom: '1.2rem', animation: 'fadeSlideUp 0.5s ease both',
  },
  heroBadgeDot: {
    width: 7, height: 7, borderRadius: '50%', background: '#22c55e',
    display: 'inline-block', animation: 'pulse 1.8s ease infinite',
  },
  heroTitle: {
    margin: '0 0 0.8rem', fontSize: 'clamp(2.2rem,4.5vw,3.5rem)',
    fontWeight: 900, lineHeight: 1.05, color: '#14532d',
    animation: 'fadeSlideUp 0.55s ease 0.08s both',
  },
  heroTitleGrad: {
    background: 'linear-gradient(135deg,#16a34a,#84cc16)',
    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
  },
  heroSub: {
    fontSize: '1rem', color: '#6b7280', lineHeight: 1.7, marginBottom: '1.8rem',
    animation: 'fadeSlideUp 0.6s ease 0.16s both',
  },
  heroBtn: {
    display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
    background: 'linear-gradient(135deg,#16a34a,#22c55e)',
    border: 'none', borderRadius: 100, color: '#fff',
    padding: '0.85rem 2rem', fontSize: '0.95rem', fontWeight: 700,
    cursor: 'pointer', fontFamily: 'inherit',
    boxShadow: '0 8px 24px rgba(22,163,74,0.35)',
    animation: 'fadeSlideUp 0.65s ease 0.22s both',
  },

  /* TODAY CARD */
  todayCard: {
    flex: '0 0 400px', maxWidth: '100%',
    background: '#fff', border: '1.5px solid #e2e8f0', borderRadius: 22,
    padding: '1.6rem 1.7rem', boxShadow: '0 8px 32px rgba(0,0,0,0.06)',
    animation: 'scaleIn 0.6s cubic-bezier(0.34,1.2,0.64,1) 0.15s both',
  },
  todayTop: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' },
  todayLabel: { fontSize: '0.68rem', fontWeight: 700, color: '#16a34a', letterSpacing: '0.14em', textTransform: 'uppercase' },
  todayDate: { fontSize: '1.05rem', fontWeight: 800, color: '#1e293b', marginTop: 2 },
  todayTime: { fontSize: '1.9rem', fontWeight: 900, color: '#14532d', fontFamily: 'monospace' },
  todayDivider: { height: 1, background: '#e2e8f0', margin: '1.1rem 0' },
  tipHead: { display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.78rem', fontWeight: 700, color: '#374151', marginBottom: '0.5rem' },
  tipIcon: { fontSize: '1rem' },
  tipText: {
    margin: 0, fontSize: '0.86rem', color: '#6b7280', lineHeight: 1.65,
    minHeight: '4.2em', animation: 'fadeSlideUp 0.5s ease both',
  },
  tipDots: { display: 'flex', gap: 6, marginTop: '0.9rem' },
  tipDot: { height: 6, borderRadius: 100, transition: 'all 0.3s ease', display: 'inline-block' },

  /* MODULES */
  modulesSection: { maxWidth: 1280, margin: '0 auto', padding: '3rem 2rem 5rem', position: 'relative', zIndex: 1 },
  sectionHeader: {
    display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between',
    gap: '1rem', marginBottom: '2rem', flexWrap: 'wrap',
  },
  sectionTag: {
    display: 'flex', alignItems: 'center', gap: '0.4rem',
    fontSize: '0.68rem', fontWeight: 700, color: '#16a34a',
    letterSpacing: '0.18em', textTransform: 'uppercase', marginBottom: '0.4rem',
  },
  sectionTagDot: { width: 7, height: 7, borderRadius: '50%', background: '#22c55e', display: 'inline-block' },
  sectionTitle: { margin: 0, fontSize: 'clamp(1.5rem,3vw,2.1rem)', fontWeight: 900, color: '#14532d' },
  sectionSub: { color: '#6b7280', fontSize: '0.9rem', maxWidth: 360, margin: 0, lineHeight: 1.6, alignSelf: 'flex-end' },

  cardsGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(260px,1fr))', gap: '1.3rem' },

  /* MODULE CARD */
  card: {
    background: '#fff', border: '1.5px solid #e2e8f0', borderRadius: 22,
    padding: '1.8rem 1.7rem', cursor: 'pointer', position: 'relative', overflow: 'hidden',
    animation: 'scaleIn 0.5s cubic-bezier(0.34,1.2,0.64,1) both',
    transition: 'transform 0.3s cubic-bezier(0.34,1.2,0.64,1), box-shadow 0.3s ease',
    userSelect: 'none', outlineOffset: 3,
  },
  cardShimmer: { position: 'absolute', inset: 0, pointerEvents: 'none', transition: 'opacity 0.3s', backgroundSize: '200% 100%' },
  ripple: {
    position: 'absolute', width: 4, height: 4, borderRadius: '50%',
    transform: 'translate(-50%,-50%)', pointerEvents: 'none', animation: 'rippleOut 0.7s ease forwards',
  },
  cardTag: {
    display: 'inline-block', fontSize: '0.6rem', fontWeight: 700,
    letterSpacing: '0.12em', textTransform: 'uppercase',
    padding: '0.22rem 0.65rem', borderRadius: 100, marginBottom: '1.2rem',
  },
  cardIconWrap: {
    width: 60, height: 60, borderRadius: 16,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    marginBottom: '1.1rem', position: 'relative',
  },
  cardIconEmoji: { fontSize: '1.7rem', position: 'relative', zIndex: 1 },
  iconRing: {
    position: 'absolute', inset: -6, borderRadius: 22, border: '2px solid',
    transition: 'opacity 0.3s', animation: 'ringPulse 1.8s ease infinite',
  },
  cardTitle: { margin: '0 0 0.45rem', fontSize: '1.05rem', fontWeight: 800, color: '#1e293b' },
  cardDesc: { margin: '0 0 1.4rem', fontSize: '0.83rem', color: '#6b7280', lineHeight: 1.65 },
  cardBtn: {
    display: 'inline-flex', alignItems: 'center', gap: '0.4rem',
    padding: '0.55rem 1.2rem', border: '1.5px solid', borderRadius: 100,
    fontSize: '0.8rem', fontWeight: 700, transition: 'all 0.25s ease', cursor: 'pointer',
  },

  /* FOOTER */
  footer: { background: '#fff', borderTop: '1px solid #e2e8f0', padding: '1.5rem 0', position: 'relative', zIndex: 1 },
  footerInner: {
    maxWidth: 1280, margin: '0 auto', padding: '0 2rem',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap',
  },
  footerLogo: { fontFamily: "'Georgia',serif", fontSize: '1.1rem', fontWeight: 900, color: '#14532d', letterSpacing: '0.08em' },
  footerCopy: { fontSize: '0.75rem', color: '#9ca3af' },
  footerLinks: { display: 'flex', gap: '1.2rem' },
  footerLink: { fontSize: '0.78rem', color: '#6b7280', cursor: 'pointer', fontWeight: 600 },
};

/* ═══════════════════════════════════════════════════════════════
   KEYFRAMES
═══════════════════════════════════════════════════════════════ */
const KEYFRAMES = `
  @keyframes fadeSlideUp {
    from { opacity:0; transform:translateY(22px); }
    to   { opacity:1; transform:translateY(0); }
  }
  @keyframes scaleIn {
    from { opacity:0; transform:scale(0.92) translateY(14px); }
    to   { opacity:1; transform:scale(1) translateY(0); }
  }
  @keyframes pulse {
    0%,100% { opacity:1; transform:scale(1); }
    50%     { opacity:0.6; transform:scale(0.88); }
  }
  @keyframes shimmer {
    0%   { background-position:200% 0; }
    100% { background-position:-200% 0; }
  }
  @keyframes rippleOut {
    from { width:4px; height:4px; opacity:0.7; }
    to   { width:340px; height:340px; opacity:0; }
  }
  @keyframes ringPulse {
    0%,100% { transform:scale(1); opacity:0.8; }
    50%     { transform:scale(1.12); opacity:0.4; }
  }
  @keyframes orbFloat1 {
    0%,100% { transform:translate(0,0) scale(1); }
    50%     { transform:translate(30px,40px) scale(1.08); }
  }
  @keyframes orbFloat2 {
    0%,100% { transform:translate(0,0) scale(1); }
    50%     { transform:translate(-25px,30px) scale(1.06); }
  }
  @keyframes orbFloat3 {
    0%,100% { transform:translate(0,0) scale(1); }
    50%     { transform:translate(20px,-35px) scale(1.1); }
  }
  @media (prefers-reduced-motion: reduce) {
    * { animation: none !important; transition: none !important; }
  }
`;