import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getMarketSummary } from '../services/api';
import toast from 'react-hot-toast';

/* ═══════════════════════════════════════════════════════════════
   ALIP — Broker Dashboard  ·  Professional Light Mode
   Features:
   · Animated counter stats
   · Glassmorphism sticky header
   · Staggered card entrance animations
   · Ripple effect on module cards
   · Live clock
   · Floating orb background
   · Hover shimmer on cards
═══════════════════════════════════════════════════════════════ */

const MODULES = [
  {
    icon:  '📊',
    title: 'Demand Analysis',
    desc:  'Analyse regional crop demand, supply gaps and market alerts',
    path:  '/demand',
    grad:  'linear-gradient(135deg,#7c3aed,#a78bfa)',
    glow:  'rgba(124,58,237,0.28)',
    tag:   'Analytics',
  },
  {
    icon:  '📦',
    title: 'All Listings',
    desc:  'Browse every active crop listing across all regions',
    path:  '/listings',
    grad:  'linear-gradient(135deg,#ea580c,#fb923c)',
    glow:  'rgba(234,88,12,0.28)',
    tag:   'Inventory',
  },
  {
    icon:  '🗺️',
    title: 'Regional Supply',
    desc:  'Check live crop supply volumes by district and state',
    path:  '/supply',
    grad:  'linear-gradient(135deg,#0284c7,#38bdf8)',
    glow:  'rgba(2,132,199,0.28)',
    tag:   'Mapping',
  },
  {
    icon:  '➕',
    title: 'Add Crop Listing',
    desc:  'Post new crop availability with pricing and quantity',
    path:  '/listing',
    grad:  'linear-gradient(135deg,#16a34a,#4ade80)',
    glow:  'rgba(22,163,74,0.28)',
    tag:   'Create',
  },
  {
    icon:  '🔔',
    title: 'Notifications',
    desc:  'View price alerts, supply updates and market signals',
    path:  '/notifications',
    grad:  'linear-gradient(135deg,#dc2626,#f87171)',
    glow:  'rgba(220,38,38,0.28)',
    tag:   'Alerts',
  },
];

/* ── Animated counter hook ── */
function useCountUp(target, duration = 1400, start = false) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (!start || !target) return;
    let raf, startTime;
    const end = Number(target) || 0;
    const tick = (t) => {
      startTime = startTime ?? t;
      const p = Math.min((t - startTime) / duration, 1);
      const ease = 1 - Math.pow(1 - p, 3);
      setVal(Math.round(end * ease));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration, start]);
  return val;
}

/* ── Live clock ── */
function useClock() {
  const [time, setTime] = useState('');
  useEffect(() => {
    const update = () => setTime(new Date().toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit' }));
    update();
    const iv = setInterval(update, 1000);
    return () => clearInterval(iv);
  }, []);
  return time;
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

/* ── Module card ── */
function ModuleCard({ mod, idx, onClick }) {
  const [hovered, setHovered] = useState(false);
  const [ripple, triggerRipple] = useRipple();
  const ref = useRef(null);

  const handleClick = (e) => {
    triggerRipple(e, ref.current);
    setTimeout(() => onClick(mod.path), 180);
  };

  return (
    <div
      ref={ref}
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
      {/* Shimmer overlay on hover */}
      <div style={{
        ...S.cardShimmer,
        opacity: hovered ? 1 : 0,
        background: `linear-gradient(105deg,transparent 40%,${mod.glow.replace('0.28','0.12')} 50%,transparent 60%)`,
        backgroundSize: '200% 100%',
        animation: hovered ? 'shimmer 1.4s ease infinite' : 'none',
      }} />

      {/* Ripple */}
      {ripple && (
        <span style={{
          ...S.ripple,
          left: ripple.x, top: ripple.y,
          background: mod.glow.replace('0.28', '0.35'),
        }} key={ripple.key} />
      )}

      {/* Tag */}
      <div style={{ ...S.cardTag, background: mod.glow.replace('0.28','0.1'), color: mod.grad.match(/#[0-9a-f]{6}/i)?.[0] || '#555' }}>
        {mod.tag}
      </div>

      {/* Icon */}
      <div style={{ ...S.cardIconWrap, background: mod.grad, boxShadow: `0 8px 20px ${mod.glow}` }}>
        <span style={S.cardIconEmoji}>{mod.icon}</span>
        {/* Glow ring */}
        <div style={{ ...S.iconRing, borderColor: mod.glow.replace('0.28','0.5'), opacity: hovered ? 1 : 0 }} />
      </div>

      <h3 style={S.cardTitle}>{mod.title}</h3>
      <p style={S.cardDesc}>{mod.desc}</p>

      {/* Open button */}
      <div style={{
        ...S.cardBtn,
        background: hovered ? mod.grad : 'transparent',
        color: hovered ? '#fff' : mod.grad.match(/#[0-9a-f]{6}/i)?.[0] || '#333',
        borderColor: mod.grad.match(/#[0-9a-f]{6}/i)?.[0] || '#ccc',
      }}>
        Open Module →
      </div>
    </div>
  );
}

/* ── Stat card ── */
function StatCard({ icon, value, label, suffix = '', delay = 0, color, start }) {
  const count = useCountUp(value, 1400, start);
  return (
    <div style={{ ...S.statCard, animationDelay: `${delay}s` }}>
      <div style={{ ...S.statIcon, background: color + '18', color }}>
        {icon}
      </div>
      <div>
        <div style={{ ...S.statValue, color }}>
          {count}{suffix}
        </div>
        <div style={S.statLabel}>{label}</div>
      </div>
    </div>
  );
}

/* ── Main component ── */
export default function BrokerDashboard() {
  const { user, logout } = useAuth();
  const navigate         = useNavigate();
  const time             = useClock();
  const [summary,  setSummary]  = useState(null);
  const [loading,  setLoading]  = useState(true);
  const [scrolled, setScrolled] = useState(false);
  const [statsVis, setStatsVis] = useState(false);
  const statsRef = useRef(null);

  useEffect(() => {
    loadSummary();
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Trigger stat animation when banner comes into view
  useEffect(() => {
    if (!statsRef.current) return;
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setStatsVis(true); obs.disconnect(); }
    }, { threshold: 0.3 });
    obs.observe(statsRef.current);
    return () => obs.disconnect();
  }, [summary]);

  const loadSummary = async () => {
    try {
      const res = await getMarketSummary();
      setSummary(res.data);
    } catch {
      toast.error('Failed to load market data!');
    }
    setLoading(false);
  };

  const handleLogout = () => {
    logout();
    toast.success('Logged out!');
    navigate('/login');
  };

  const cropCount = summary
    ? Object.keys(
        Object.values(summary.regional_summary || {}).reduce((a, b) => ({ ...a, ...b }), {})
      ).length
    : 0;

  return (
    <div style={S.page}>
      <style>{KEYFRAMES}</style>

      {/* ── Floating background orbs ── */}
      <div style={S.orb1} />
      <div style={S.orb2} />
      <div style={S.orb3} />

      {/* ═══ HEADER ═══ */}
      <header style={{
        ...S.header,
        background: scrolled ? 'rgba(255,255,255,0.92)' : 'rgba(255,255,255,0.75)',
        boxShadow:  scrolled ? '0 4px 30px rgba(0,0,0,0.10)' : '0 1px 0 rgba(0,0,0,0.06)',
        backdropFilter: 'blur(20px)',
      }}>
        <div style={S.headerInner}>

          {/* Logo */}
          <div style={S.logoWrap}>
            <div style={S.logoBadge}>
              <span style={S.logoLeaf}>🌿</span>
            </div>
            <div>
              <div style={S.logoText}>ALIP<span style={S.logoDot}>.</span></div>
              <div style={S.logoSub}>Broker Dashboard</div>
            </div>
          </div>

          {/* Centre: nav pills */}
          <nav style={S.nav}>
            {['Dashboard','Market','Listings','Reports'].map((item, i) => (
              <button key={i} style={{
                ...S.navPill,
                ...(i === 0 ? S.navPillActive : {}),
              }}>
                {item}
              </button>
            ))}
          </nav>

          {/* Right side */}
          <div style={S.headerRight}>
            {/* Clock */}
            <div style={S.clockWrap}>
              <span style={S.clockDot} />
              <span style={S.clockTime}>{time}</span>
            </div>

            {/* User avatar */}
            <div style={S.avatarWrap}>
              <div style={S.avatar}>
                {user?.full_name?.[0]?.toUpperCase() || 'B'}
              </div>
              <div style={S.avatarInfo}>
                <div style={S.avatarName}>{user?.full_name || 'Broker'}</div>
                <div style={S.avatarRole}>🏪 Market Broker</div>
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

      {/* ═══ HERO BANNER ═══ */}
      <section style={S.hero}>
        <div style={S.heroContent}>
          {/* Left text */}
          <div style={S.heroLeft}>
            <div style={S.heroBadge}>
              <span style={S.heroBadgeDot} /> Farmer Listing Data
            </div>
            <h1 style={S.heroTitle}>
              Market<br />
              <span style={S.heroTitleGrad}>Overview</span>
            </h1>
            <p style={S.heroSub}>
              Crop supply from farmer listings, demand gaps and
              regional market signals — all in one place.
            </p>
            <button style={S.heroBtn} onClick={() => navigate('/demand')}>
              View Demand Analysis →
            </button>
          </div>

          {/* Right: stat cards */}
          <div ref={statsRef} style={S.statsGrid}>
            {loading ? (
              <div style={S.loadingWrap}>
                <div style={S.loadingSpinner} />
                <p style={{ color:'#9ca3af', margin:0 }}>Loading market data…</p>
              </div>
            ) : summary ? (
              <>
                <StatCard
                  icon="📋" value={summary.total_listings}
                  label="Total Listings" color="#7c3aed" delay={0.1} start={statsVis}
                />
                <StatCard
                  icon="🗺️" value={summary.regions_active}
                  label="Active Regions" color="#0284c7" delay={0.18} start={statsVis}
                />
                <StatCard
                  icon="🌾" value={cropCount}
                  label="Crop Types" color="#16a34a" delay={0.26} start={statsVis}
                />
                <StatCard
                  icon="⚖️" value={Math.round(summary.total_quantity_kg || 0)}
                  label="Kg Listed" color="#ea580c" delay={0.34} start={statsVis}
                />
              </>
            ) : (
              <div style={S.loadingWrap}>
                <p style={{ color:'#9ca3af' }}>No data available yet.</p>
              </div>
            )}
          </div>
        </div>

        {/* Decorative grid lines */}
        <div style={S.heroGrid} />
      </section>

      {/* ═══ MODULE CARDS ═══ */}
      <section style={S.modulesSection}>
        {/* Section header */}
        <div style={S.sectionHeader}>
          <div style={S.sectionLeft}>
            <div style={S.sectionTag}>
              <span style={S.sectionTagDot} />
              Broker Modules
            </div>
            <h2 style={S.sectionTitle}>Your Tools</h2>
          </div>
          <p style={S.sectionSub}>
            Select a module to get started. All tools are connected to live market data.
          </p>
        </div>

        {/* Cards grid */}
        <div style={S.cardsGrid}>
          {MODULES.map((mod, idx) => (
            <ModuleCard
              key={mod.path}
              mod={mod}
              idx={idx}
              onClick={navigate}
            />
          ))}

          {/* Placeholder "Coming Soon" card */}
          <div style={S.comingSoonCard}>
            <div style={S.comingSoonIcon}>🚀</div>
            <div style={S.comingSoonTitle}>More coming soon</div>
            <p style={S.comingSoonDesc}>
              Trade history, price forecasting and farmer messaging
              are in development.
            </p>
          </div>
        </div>
      </section>

      {/* ═══ FOOTER ═══ */}
      <footer style={S.footer}>
        <div style={S.footerInner}>
          <span style={S.footerLogo}>ALIP<span style={S.logoDot}>.</span></span>
          <span style={S.footerCopy}>© 2024 AgriLink Intelligence Platform · Broker Module</span>
          <div style={S.footerLinks}>
            {['Home','AI Engine','Supplements','Contact'].map((l, i) => (
              <span key={i} style={S.footerLink}>{l}</span>
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
  /* PAGE */
  page: {
    minHeight:  '100vh',
    background: 'linear-gradient(160deg,#f0fdf4 0%,#f8fafc 50%,#f0f4ff 100%)',
    fontFamily: "'Segoe UI','Outfit',sans-serif",
    color:      '#1e293b',
    overflowX:  'hidden',
    position:   'relative',
  },

  /* FLOATING ORBS */
  orb1: {
    position:'fixed', top:-120, left:-80, width:400, height:400,
    borderRadius:'50%', pointerEvents:'none', zIndex:0,
    background:'radial-gradient(circle,rgba(134,239,172,0.18) 0%,transparent 70%)',
    animation:'orbFloat1 12s ease-in-out infinite',
  },
  orb2: {
    position:'fixed', top:'30%', right:-100, width:350, height:350,
    borderRadius:'50%', pointerEvents:'none', zIndex:0,
    background:'radial-gradient(circle,rgba(147,197,253,0.15) 0%,transparent 70%)',
    animation:'orbFloat2 15s ease-in-out infinite',
  },
  orb3: {
    position:'fixed', bottom:-80, left:'35%', width:300, height:300,
    borderRadius:'50%', pointerEvents:'none', zIndex:0,
    background:'radial-gradient(circle,rgba(216,180,254,0.12) 0%,transparent 70%)',
    animation:'orbFloat3 18s ease-in-out infinite',
  },

  /* HEADER */
  header: {
    position:   'sticky', top:0, zIndex:100,
    borderBottom:'1px solid rgba(0,0,0,0.06)',
    transition: 'all 0.35s ease',
  },
  headerInner: {
    maxWidth:       1280, margin:'0 auto',
    padding:        '0.85rem 2rem',
    display:        'flex', alignItems:'center',
    justifyContent: 'space-between', gap:'1rem',
  },
  logoWrap: { display:'flex', alignItems:'center', gap:'0.7rem', flexShrink:0 },
  logoBadge: {
    width:36, height:36, borderRadius:10,
    background:'linear-gradient(135deg,#16a34a,#4ade80)',
    display:'flex', alignItems:'center', justifyContent:'center',
    boxShadow:'0 4px 12px rgba(22,163,74,0.35)',
  },
  logoLeaf:  { fontSize:'1.1rem' },
  logoText:  { fontFamily:"'Georgia',serif", fontSize:'1.3rem', fontWeight:900, color:'#14532d', letterSpacing:'0.07em' },
  logoDot:   { color:'#84cc16' },
  logoSub:   { fontSize:'0.65rem', color:'#6b7280', fontWeight:600, letterSpacing:'0.08em', textTransform:'uppercase' },

  nav: { display:'flex', gap:'0.3rem', flex:1, justifyContent:'center' },
  navPill: {
    padding:'0.4rem 1rem', borderRadius:100,
    border:'1px solid transparent',
    background:'transparent', color:'#6b7280',
    fontSize:'0.82rem', fontWeight:600, cursor:'pointer',
    fontFamily:'inherit', transition:'all 0.2s',
  },
  navPillActive: {
    background:'#f0fdf4', borderColor:'#bbf7d0', color:'#15803d',
  },

  headerRight: { display:'flex', alignItems:'center', gap:'0.8rem', flexShrink:0 },
  clockWrap: {
    display:'flex', alignItems:'center', gap:'0.4rem',
    background:'#f8fafc', border:'1px solid #e2e8f0',
    borderRadius:100, padding:'0.3rem 0.9rem',
  },
  clockDot: {
    width:7, height:7, borderRadius:'50%',
    background:'#22c55e', display:'inline-block',
    animation:'pulse 2s ease infinite',
  },
  clockTime: { fontSize:'0.78rem', fontWeight:700, color:'#374151', fontFamily:'monospace' },

  avatarWrap: { display:'flex', alignItems:'center', gap:'0.5rem' },
  avatar: {
    width:36, height:36, borderRadius:'50%',
    background:'linear-gradient(135deg,#16a34a,#22c55e)',
    color:'#fff', fontSize:'0.9rem', fontWeight:800,
    display:'flex', alignItems:'center', justifyContent:'center',
    boxShadow:'0 3px 10px rgba(22,163,74,0.35)',
  },
  avatarName: { fontSize:'0.8rem', fontWeight:700, color:'#1e293b' },
  avatarRole: { fontSize:'0.65rem', color:'#6b7280' },

  profileBtn: {
    padding:'0.42rem 1rem', background:'#f0fdf4',
    border:'1.5px solid #bbf7d0', borderRadius:100,
    color:'#15803d', fontSize:'0.78rem', fontWeight:700,
    cursor:'pointer', fontFamily:'inherit',
  },
  logoutBtn: {
    padding:'0.42rem 1rem', background:'#fff1f2',
    border:'1.5px solid #fecdd3', borderRadius:100,
    color:'#dc2626', fontSize:'0.78rem', fontWeight:700,
    cursor:'pointer', fontFamily:'inherit',
  },

  /* HERO */
  hero: {
    position:'relative', overflow:'hidden', zIndex:1,
    padding:'4rem 2rem 3rem',
    background:'linear-gradient(135deg,rgba(240,253,244,0.8) 0%,rgba(240,244,255,0.9) 100%)',
    borderBottom:'1px solid #e2e8f0',
  },
  heroGrid: {
    position:'absolute', inset:0, pointerEvents:'none',
    backgroundImage:
      'linear-gradient(rgba(22,163,74,0.04) 1px,transparent 1px),' +
      'linear-gradient(90deg,rgba(22,163,74,0.04) 1px,transparent 1px)',
    backgroundSize:'50px 50px',
  },
  heroContent: {
    maxWidth:1280, margin:'0 auto',
    display:'flex', alignItems:'center',
    justifyContent:'space-between', gap:'3rem',
    flexWrap:'wrap', position:'relative', zIndex:1,
  },
  heroLeft: { maxWidth:480 },
  heroBadge: {
    display:'inline-flex', alignItems:'center', gap:'0.5rem',
    background:'rgba(22,163,74,0.08)', border:'1px solid #bbf7d0',
    borderRadius:100, padding:'0.35rem 1rem',
    fontSize:'0.72rem', fontWeight:700, color:'#15803d',
    marginBottom:'1.2rem',
    animation:'fadeSlideUp 0.5s ease both',
  },
  heroBadgeDot: {
    width:7, height:7, borderRadius:'50%',
    background:'#22c55e', display:'inline-block',
    animation:'pulse 1.8s ease infinite',
  },
  heroTitle: {
    margin:'0 0 0.8rem',
    fontSize:'clamp(2.2rem,4.5vw,3.5rem)',
    fontWeight:900, lineHeight:1.05, color:'#14532d',
    animation:'fadeSlideUp 0.55s ease 0.08s both',
  },
  heroTitleGrad: {
    background:'linear-gradient(135deg,#16a34a,#84cc16)',
    WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent',
    backgroundClip:'text',
  },
  heroSub: {
    fontSize:'1rem', color:'#6b7280', lineHeight:1.7,
    marginBottom:'1.8rem',
    animation:'fadeSlideUp 0.6s ease 0.16s both',
  },
  heroBtn: {
    display:'inline-flex', alignItems:'center', gap:'0.5rem',
    background:'linear-gradient(135deg,#16a34a,#22c55e)',
    border:'none', borderRadius:100, color:'#fff',
    padding:'0.85rem 2rem', fontSize:'0.95rem', fontWeight:700,
    cursor:'pointer', fontFamily:'inherit',
    boxShadow:'0 8px 24px rgba(22,163,74,0.35)',
    animation:'fadeSlideUp 0.65s ease 0.22s both',
    transition:'all 0.25s ease',
  },

  /* STATS GRID */
  statsGrid: {
    display:'grid', gridTemplateColumns:'1fr 1fr',
    gap:'1rem', flex:'0 0 440px',
    animation:'fadeSlideUp 0.6s ease 0.1s both',
  },
  statCard: {
    background:'#fff',
    border:'1.5px solid #e2e8f0',
    borderRadius:18, padding:'1.4rem 1.5rem',
    display:'flex', alignItems:'center', gap:'1rem',
    boxShadow:'0 4px 20px rgba(0,0,0,0.05)',
    animation:'scaleIn 0.5s cubic-bezier(0.34,1.2,0.64,1) both',
    transition:'transform 0.25s, box-shadow 0.25s',
  },
  statIcon: {
    width:48, height:48, borderRadius:13, flexShrink:0,
    display:'flex', alignItems:'center', justifyContent:'center',
    fontSize:'1.4rem',
  },
  statValue: {
    fontSize:'1.9rem', fontWeight:900, lineHeight:1,
    marginBottom:'0.2rem',
  },
  statLabel: { fontSize:'0.72rem', fontWeight:600, color:'#9ca3af', textTransform:'uppercase', letterSpacing:'0.08em' },

  loadingWrap: {
    gridColumn:'1 / -1', display:'flex', flexDirection:'column',
    alignItems:'center', justifyContent:'center', gap:'0.8rem',
    padding:'2rem',
  },
  loadingSpinner: {
    width:32, height:32, borderRadius:'50%',
    border:'3px solid #e2e8f0', borderTopColor:'#16a34a',
    animation:'spin 0.7s linear infinite',
  },

  /* MODULES */
  modulesSection: {
    maxWidth:1280, margin:'0 auto',
    padding:'3rem 2rem 5rem',
    position:'relative', zIndex:1,
  },
  sectionHeader: {
    display:'flex', alignItems:'flex-end',
    justifyContent:'space-between', gap:'1rem',
    marginBottom:'2rem', flexWrap:'wrap',
  },
  sectionLeft: {},
  sectionTag: {
    display:'flex', alignItems:'center', gap:'0.4rem',
    fontSize:'0.68rem', fontWeight:700, color:'#16a34a',
    letterSpacing:'0.18em', textTransform:'uppercase',
    marginBottom:'0.4rem',
  },
  sectionTagDot: {
    width:7, height:7, borderRadius:'50%',
    background:'#22c55e', display:'inline-block',
  },
  sectionTitle: {
    margin:0, fontSize:'clamp(1.6rem,3vw,2.2rem)',
    fontWeight:900, color:'#14532d',
  },
  sectionSub: {
    color:'#6b7280', fontSize:'0.9rem', maxWidth:360,
    margin:0, lineHeight:1.6, alignSelf:'flex-end',
  },

  cardsGrid: {
    display:'grid',
    gridTemplateColumns:'repeat(auto-fill,minmax(260px,1fr))',
    gap:'1.3rem',
  },

  /* MODULE CARD */
  card: {
    background:'#fff', border:'1.5px solid #e2e8f0',
    borderRadius:22, padding:'1.8rem 1.7rem',
    cursor:'pointer', position:'relative', overflow:'hidden',
    animation:'scaleIn 0.5s cubic-bezier(0.34,1.2,0.64,1) both',
    transition:'transform 0.3s cubic-bezier(0.34,1.2,0.64,1), box-shadow 0.3s ease',
    userSelect:'none',
  },
  cardShimmer: {
    position:'absolute', inset:0, pointerEvents:'none',
    transition:'opacity 0.3s',
    backgroundSize:'200% 100%',
  },
  ripple: {
    position:'absolute', width:4, height:4,
    borderRadius:'50%', transform:'translate(-50%,-50%)',
    pointerEvents:'none',
    animation:'rippleOut 0.7s ease forwards',
  },
  cardTag: {
    display:'inline-block', fontSize:'0.6rem', fontWeight:700,
    letterSpacing:'0.12em', textTransform:'uppercase',
    padding:'0.22rem 0.65rem', borderRadius:100,
    marginBottom:'1.2rem',
  },
  cardIconWrap: {
    width:60, height:60, borderRadius:16,
    display:'flex', alignItems:'center', justifyContent:'center',
    marginBottom:'1.1rem', position:'relative',
    transition:'transform 0.3s ease',
  },
  cardIconEmoji: { fontSize:'1.7rem', position:'relative', zIndex:1 },
  iconRing: {
    position:'absolute', inset:-6,
    borderRadius:22, border:'2px solid',
    transition:'opacity 0.3s',
    animation:'ringPulse 1.8s ease infinite',
  },
  cardTitle: {
    margin:'0 0 0.45rem', fontSize:'1.05rem',
    fontWeight:800, color:'#1e293b',
  },
  cardDesc: {
    margin:'0 0 1.4rem', fontSize:'0.83rem',
    color:'#6b7280', lineHeight:1.65,
  },
  cardBtn: {
    display:'inline-flex', alignItems:'center', gap:'0.4rem',
    padding:'0.55rem 1.2rem', border:'1.5px solid',
    borderRadius:100, fontSize:'0.8rem', fontWeight:700,
    transition:'all 0.25s ease', cursor:'pointer',
  },

  /* COMING SOON */
  comingSoonCard: {
    background:'linear-gradient(135deg,#f8fafc,#f0f9ff)',
    border:'2px dashed #e2e8f0', borderRadius:22,
    padding:'2rem', textAlign:'center',
    display:'flex', flexDirection:'column',
    alignItems:'center', justifyContent:'center',
    animation:'scaleIn 0.5s cubic-bezier(0.34,1.2,0.64,1) 0.5s both',
  },
  comingSoonIcon:  { fontSize:'2.5rem', marginBottom:'0.7rem', opacity:0.5 },
  comingSoonTitle: { fontSize:'1rem', fontWeight:800, color:'#94a3b8', marginBottom:'0.4rem' },
  comingSoonDesc:  { fontSize:'0.8rem', color:'#94a3b8', lineHeight:1.6, margin:0 },

  /* FOOTER */
  footer: {
    background:'#fff', borderTop:'1px solid #e2e8f0',
    padding:'1.5rem 0',
  },
  footerInner: {
    maxWidth:1280, margin:'0 auto',
    padding:'0 2rem',
    display:'flex', alignItems:'center',
    justifyContent:'space-between', gap:'1rem', flexWrap:'wrap',
  },
  footerLogo: { fontFamily:"'Georgia',serif", fontSize:'1.1rem', fontWeight:900, color:'#14532d', letterSpacing:'0.08em' },
  footerCopy: { fontSize:'0.75rem', color:'#9ca3af' },
  footerLinks: { display:'flex', gap:'1.2rem' },
  footerLink:  { fontSize:'0.78rem', color:'#6b7280', cursor:'pointer', fontWeight:600 },
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
    to   { opacity:1; transform:scale(1)    translateY(0); }
  }
  @keyframes pulse {
    0%,100% { opacity:1; transform:scale(1); }
    50%     { opacity:0.6; transform:scale(0.88); }
  }
  @keyframes spin {
    to { transform:rotate(360deg); }
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
    0%,100% { transform:scale(1);   opacity:0.8; }
    50%     { transform:scale(1.12); opacity:0.4; }
  }
  @keyframes orbFloat1 {
    0%,100% { transform:translate(0,0)    scale(1); }
    50%     { transform:translate(30px,40px) scale(1.08); }
  }
  @keyframes orbFloat2 {
    0%,100% { transform:translate(0,0)     scale(1); }
    50%     { transform:translate(-25px,30px) scale(1.06); }
  }
  @keyframes orbFloat3 {
    0%,100% { transform:translate(0,0)    scale(1); }
    50%     { transform:translate(20px,-35px) scale(1.1); }
  }
`;