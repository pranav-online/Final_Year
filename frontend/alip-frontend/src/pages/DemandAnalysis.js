import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDemandAnalysis } from '../services/api';
import toast from 'react-hot-toast';

/* ═══════════════════════════════════════════════════════════════
   ALIP — Demand Analysis  (Broker Dashboard)  — Light Mode
═══════════════════════════════════════════════════════════════ */

export default function DemandAnalysis() {
  const navigate              = useNavigate();
  const [region, setRegion]   = useState('');
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!region.trim()) { toast.error('Enter a region name!'); return; }
    setLoading(true);
    try {
      const res = await getDemandAnalysis(region);
      setResult(res.data);
      toast.success('Analysis complete!');
    } catch {
      toast.error('Failed to analyse region.');
    }
    setLoading(false);
  };

  return (
    <div style={s.page}>

      {/* ═══ HEADER ═══ */}
      <div style={s.header}>
        <div style={s.headerInner}>

          {/* Logo */}
          <div style={s.headerLeft}>
            <div style={s.logoBox}>🌿</div>
            <span style={s.logoText}>
              ALIP<span style={s.logoDot}>.</span>
            </span>
          </div>

          {/* Centre title */}
          <div style={s.headerMid}>
            <div style={s.pageTag}>
              <span style={s.tagLine} />
              Broker Module
              <span style={s.tagLine} />
            </div>
            <h1 style={s.headerTitle}>📊 Demand Analysis</h1>
          </div>

          {/* Back button */}
          <button style={s.backBtn} onClick={() => navigate('/broker')}>
            ← Back to Dashboard
          </button>

        </div>
      </div>

      {/* ═══ BODY ═══ */}
      <div style={s.body}>

        {/* ── Search card ── */}
        <div style={s.searchCard}>
          <div style={s.cardTopStrip} />

          <div style={s.cardTag}>Regional Intelligence</div>
          <h2 style={s.cardH2}>Analyse Regional Demand</h2>
          <p style={s.cardSub}>
            Enter a city or district to view market supply–demand
            balance, alerts and redistribution options.
          </p>

          <div style={s.searchRow}>
            <div style={s.inputWrap}>
              <span style={s.inputIcon}>📍</span>
              <input
                style={s.input}
                placeholder="e.g. Hyderabad, Chennai, Pune…"
                value={region}
                onChange={e => setRegion(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              />
            </div>
            <button
              style={{ ...s.searchBtn, opacity: loading ? 0.7 : 1 }}
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading ? '⏳ Analysing…' : '🔍 Analyse'}
            </button>
          </div>

          {/* Quick city pills */}
          <div style={s.quickRow}>
            {['Hyderabad','Chennai','Mumbai','Delhi','Bangalore','Pune','Kolkata'].map(c => (
              <button key={c} style={s.quickPill} onClick={() => setRegion(c)}>
                📍 {c}
              </button>
            ))}
          </div>
        </div>

        {/* ── Results ── */}
        {result && (
          <>
            {/* ── Market Alerts ── */}
            {result.alerts?.length > 0 && (
              <div style={s.section}>
                <div style={s.sectionLabel}>
                  <span style={s.sectionDot} />
                  Market Alerts
                  <span style={s.alertCount}>{result.total_alerts}</span>
                </div>

                <div style={s.alertsGrid}>
                  {result.alerts.map((alert, idx) => {
                    const isOver = alert.type === 'oversupply';
                    return (
                      <div key={idx} style={{
                        ...s.alertCard,
                        borderLeftColor: isOver ? '#ef4444' : '#f59e0b',
                        background: isOver ? '#fff5f5' : '#fffbf0',
                      }}>
                        <div style={s.alertTop}>
                          <div style={{
                            ...s.alertIconBox,
                            background: isOver ? '#fee2e2' : '#fef3c7',
                          }}>
                            {isOver ? '📈' : '📉'}
                          </div>
                          <span style={{
                            ...s.alertBadge,
                            background:  isOver ? '#fee2e2' : '#fef3c7',
                            color:       isOver ? '#991b1b' : '#92400e',
                          }}>
                            {isOver ? 'Oversupply' : 'Undersupply'}
                          </span>
                        </div>
                        <p style={s.alertMsg}>{alert.message}</p>
                        <div style={{
                          ...s.alertActionBox,
                          borderLeftColor: isOver ? '#ef4444' : '#f59e0b',
                        }}>
                          <span style={s.actionLabel}>💡 Action</span>
                          <span style={s.actionText}>{alert.action}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* ── Market Balance ── */}
            <div style={s.section}>
              <div style={s.sectionLabel}>
                <span style={s.sectionDot} />
                Market Balance —&nbsp;<strong>{result.region}</strong>
              </div>
              <p style={s.balanceNote}>
                Expected demand is estimated from the crop, season and regional market profile.
              </p>

              <div style={s.cropsGrid}>
                {Object.entries(result.crop_analysis || {}).map(([crop, item]) => {
                  const status = item.market_status;
                  const badge  = STATUS_BADGE[status] || STATUS_BADGE.balanced;
                  const ratio  = parseFloat(item.supply_demand_ratio);
                  const barPct = Math.min(ratio * 50, 100);

                  return (
                    <div key={crop} style={s.cropCard}>
                      {/* coloured left border */}
                      <div style={{ ...s.cropAccent, background: badge.accent }} />

                      {/* Header row */}
                      <div style={s.cropHeader}>
                        <div style={s.cropLeft}>
                          <div style={{
                            ...s.cropIconBox,
                            background: badge.iconBg,
                          }}>
                            🌾
                          </div>
                          <div>
                            <div style={s.cropName}>
                              {crop.charAt(0).toUpperCase() + crop.slice(1)}
                            </div>
                            {item.description && (
                              <div style={s.cropDesc}>{item.description}</div>
                            )}
                          </div>
                        </div>
                        <span style={{ ...s.statusBadge, ...badge.badge }}>
                          {status}
                        </span>
                      </div>

                      {/* Metrics strip */}
                      <div style={s.metricsRow}>
                        <div style={s.metricBox}>
                          <div style={s.metricVal}>{item.current_supply_kg} kg</div>
                          <div style={s.metricLbl}>Available Supply</div>
                        </div>
                        <div style={s.metricDivider} />
                        <div style={s.metricBox}>
                          <div style={s.metricVal}>{item.expected_demand_kg} kg</div>
                          <div style={s.metricLbl}>Expected Demand</div>
                        </div>
                        <div style={s.metricDivider} />
                        <div style={s.metricBox}>
                          <div style={{ ...s.metricVal, color: badge.accent }}>
                            {item.supply_demand_ratio}×
                          </div>
                          <div style={s.metricLbl}>Supply / Demand</div>
                        </div>
                      </div>

                      {/* Ratio progress bar */}
                      <div style={s.barTrack}>
                        <div style={{
                          ...s.barFill,
                          width: `${barPct}%`,
                          background: badge.bar,
                        }} />
                      </div>
                      <div style={s.barLabels}>
                        <span>0×</span><span>Balanced (1×)</span><span>2×</span>
                      </div>

                      {/* Recommendation */}
                      <div style={s.recBox}>
                        <span style={s.recIcon}>💡</span>
                        <p style={s.recText}>{item.recommendation}</p>
                      </div>

                      {/* Redistribution */}
                      {item.redistribution_options?.length > 0 && (
                        <div style={s.redistSection}>
                          <div style={s.redistTitle}>Redistribution Options</div>
                          <div style={s.redistRow}>
                            {item.redistribution_options.map(opt => (
                              <div key={opt.region} style={s.redistPill}>
                                <span style={s.redistArrow}>
                                  {opt.direction === 'send_to' ? '→' : '←'}
                                </span>
                                <span>
                                  {opt.direction === 'send_to' ? 'Send to' : 'Source from'}{' '}
                                  <strong>{opt.region}</strong>{' · '}{opt.suggested_quantity_kg} kg
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Price impact */}
                      {item.price_impact && (
                        <div style={s.priceBox}>
                          <span style={s.priceIcon}>📉</span>
                          <p style={s.priceText}>
                            Est. price pressure:{' '}
                            <strong>{item.price_impact.price_drop_pct}% drop</strong>
                            {' · '}{item.price_impact.recommendation}
                          </p>
                        </div>
                      )}
                    </div>
                  );
                })}

                {Object.keys(result.crop_analysis || {}).length === 0 && (
                  <div style={s.emptyBox}>
                    <div style={s.emptyIcon}>📦</div>
                    <div style={s.emptyTitle}>No crop data available</div>
                    <div style={s.emptySub}>
                      No supply records found for this region.
                    </div>
                  </div>
                )}
              </div>
            </div>
          </>
        )}

        {/* ── Initial empty state ── */}
        {!result && !loading && (
          <div style={s.emptyState}>
            <div style={s.emptyStateEmoji}>📊</div>
            <div style={s.emptyStateTitle}>Enter a Region to Begin</div>
            <p style={s.emptyStateSub}>
              Type a city or district above to view real-time market
              supply–demand balance, alerts and redistribution recommendations.
            </p>
          </div>
        )}

      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   STATUS BADGE CONFIG
═══════════════════════════════════════════════════════════════ */
const STATUS_BADGE = {
  oversupply: {
    accent: '#ef4444',
    iconBg: '#fee2e2',
    bar:    'linear-gradient(90deg,#ef4444,#f97316)',
    badge:  { background: '#fee2e2', color: '#991b1b' },
  },
  undersupply: {
    accent: '#f59e0b',
    iconBg: '#fef3c7',
    bar:    'linear-gradient(90deg,#f59e0b,#84cc16)',
    badge:  { background: '#fef3c7', color: '#92400e' },
  },
  balanced: {
    accent: '#22c55e',
    iconBg: '#dcfce7',
    bar:    'linear-gradient(90deg,#22c55e,#16a34a)',
    badge:  { background: '#dcfce7', color: '#166534' },
  },
};

/* ═══════════════════════════════════════════════════════════════
   STYLES  — clean light mode
═══════════════════════════════════════════════════════════════ */
const s = {

  /* PAGE */
  page: {
    minHeight: '100vh',
    background: '#f0f4f0',
    fontFamily: "'Segoe UI','Outfit',sans-serif",
    color: '#1a2e1a',
  },

  /* ── HEADER ── */
  header: {
    position: 'sticky', top: 0, zIndex: 100,
    background: '#ffffff',
    borderBottom: '1px solid #d1e7d1',
    boxShadow: '0 2px 12px rgba(34,118,50,0.08)',
  },
  headerInner: {
    maxWidth: 1100, margin: '0 auto',
    padding: '0.9rem 2rem',
    display: 'flex', alignItems: 'center',
    justifyContent: 'space-between', gap: '1rem',
  },
  headerLeft: { display: 'flex', alignItems: 'center', gap: '0.55rem' },
  logoBox: {
    width: 34, height: 34, borderRadius: 9,
    background: 'linear-gradient(135deg,#16a34a,#22c55e)',
    display: 'flex', alignItems: 'center',
    justifyContent: 'center', fontSize: '1rem',
  },
  logoText: {
    fontFamily: "'Georgia',serif",
    fontSize: '1.3rem', fontWeight: 900,
    color: '#14532d', letterSpacing: '0.08em',
  },
  logoDot: { color: '#84cc16' },

  headerMid: { textAlign: 'center', flex: 1 },
  pageTag: {
    fontSize: '0.6rem', letterSpacing: '0.2em',
    textTransform: 'uppercase', color: '#16a34a',
    display: 'flex', alignItems: 'center',
    justifyContent: 'center', gap: '0.5rem',
    marginBottom: '0.1rem',
  },
  tagLine: {
    display: 'inline-block', width: 22,
    height: 1, background: '#16a34a',
  },
  headerTitle: {
    margin: 0, fontSize: 'clamp(1rem,2.2vw,1.35rem)',
    fontWeight: 800, color: '#14532d',
  },

  backBtn: {
    background: '#f0fdf4',
    border: '1.5px solid #bbf7d0',
    color: '#15803d', borderRadius: 100,
    padding: '0.4rem 1rem',
    fontSize: '0.78rem', fontWeight: 600,
    cursor: 'pointer', whiteSpace: 'nowrap',
  },

  /* ── BODY ── */
  body: {
    maxWidth: 1100, margin: '0 auto',
    padding: '2rem 2rem 5rem',
  },

  /* ── SEARCH CARD ── */
  searchCard: {
    background: '#ffffff',
    border: '1.5px solid #d1e7d1',
    borderRadius: 20,
    padding: '2rem 2.5rem',
    marginBottom: '2rem',
    boxShadow: '0 4px 24px rgba(34,118,50,0.07)',
    position: 'relative', overflow: 'hidden',
  },
  cardTopStrip: {
    position: 'absolute', top: 0, left: 0, right: 0,
    height: 4,
    background: 'linear-gradient(90deg,#16a34a,#84cc16,#22c55e)',
    borderRadius: '20px 20px 0 0',
  },
  cardTag: {
    fontSize: '0.6rem', letterSpacing: '0.22em',
    textTransform: 'uppercase', color: '#16a34a',
    fontWeight: 700, marginBottom: '0.4rem',
  },
  cardH2: {
    margin: '0 0 0.35rem',
    color: '#14532d',
    fontSize: 'clamp(1.3rem,3vw,1.9rem)',
    fontWeight: 900,
  },
  cardSub: {
    color: '#6b7280', fontSize: '0.88rem',
    lineHeight: 1.65, marginBottom: '1.5rem',
  },

  searchRow: { display: 'flex', gap: '0.8rem', maxWidth: 580 },
  inputWrap: {
    flex: 1, position: 'relative',
    display: 'flex', alignItems: 'center',
  },
  inputIcon: {
    position: 'absolute', left: '0.85rem',
    fontSize: '1rem', pointerEvents: 'none',
  },
  input: {
    width: '100%',
    background: '#f9fafb',
    border: '1.5px solid #d1fae5',
    borderRadius: 10,
    padding: '0.75rem 1rem 0.75rem 2.6rem',
    color: '#1a2e1a', fontSize: '0.95rem',
    outline: 'none', fontFamily: 'inherit',
    transition: 'border-color 0.2s',
    boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.04)',
  },
  searchBtn: {
    background: 'linear-gradient(135deg,#16a34a,#22c55e)',
    border: 'none', borderRadius: 10,
    color: '#fff', fontWeight: 700,
    fontSize: '0.92rem', padding: '0.75rem 1.8rem',
    cursor: 'pointer', whiteSpace: 'nowrap',
    fontFamily: 'inherit',
    boxShadow: '0 4px 14px rgba(34,197,94,0.3)',
    transition: 'all 0.25s',
  },

  quickRow: {
    display: 'flex', gap: '0.5rem',
    flexWrap: 'wrap', marginTop: '1.2rem',
  },
  quickPill: {
    background: '#f0fdf4',
    border: '1px solid #bbf7d0',
    borderRadius: 100,
    padding: '0.28rem 0.85rem',
    fontSize: '0.75rem', color: '#16a34a',
    cursor: 'pointer', fontFamily: 'inherit',
    fontWeight: 600, transition: 'all 0.2s',
  },

  /* ── SECTION LABEL ── */
  section: { marginBottom: '2rem' },
  sectionLabel: {
    display: 'flex', alignItems: 'center', gap: '0.6rem',
    fontSize: '0.88rem', fontWeight: 700,
    color: '#14532d', marginBottom: '1rem',
  },
  sectionDot: {
    width: 8, height: 8, borderRadius: '50%',
    background: '#22c55e', display: 'inline-block', flexShrink: 0,
  },
  alertCount: {
    background: '#dcfce7', color: '#166534',
    borderRadius: 100, fontSize: '0.7rem',
    fontWeight: 700, padding: '0.15rem 0.55rem',
  },
  balanceNote: {
    color: '#6b7280', fontSize: '0.82rem',
    margin: '-0.4rem 0 1.2rem',
  },

  /* ── ALERTS GRID ── */
  alertsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill,minmax(280px,1fr))',
    gap: '1rem',
  },
  alertCard: {
    background: '#fff',
    border: '1px solid #e5e7eb',
    borderLeft: '4px solid #ef4444',
    borderRadius: 14,
    padding: '1.2rem 1.4rem',
    boxShadow: '0 2px 10px rgba(0,0,0,0.05)',
  },
  alertTop: {
    display: 'flex', alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '0.75rem',
  },
  alertIconBox: {
    width: 38, height: 38, borderRadius: 9,
    display: 'flex', alignItems: 'center',
    justifyContent: 'center', fontSize: '1.15rem',
  },
  alertBadge: {
    fontSize: '0.64rem', fontWeight: 700,
    letterSpacing: '0.06em', textTransform: 'uppercase',
    padding: '0.25rem 0.75rem', borderRadius: 100,
  },
  alertMsg: {
    margin: '0 0 0.75rem',
    color: '#374151', fontSize: '0.84rem', lineHeight: 1.6,
  },
  alertActionBox: {
    background: '#f9fafb',
    border: '1px solid #e5e7eb',
    borderLeft: '3px solid #ef4444',
    borderRadius: 8,
    padding: '0.55rem 0.85rem',
    display: 'flex', gap: '0.5rem',
    alignItems: 'flex-start',
  },
  actionLabel: {
    color: '#16a34a', fontSize: '0.72rem',
    fontWeight: 700, whiteSpace: 'nowrap', paddingTop: 1,
  },
  actionText: { color: '#6b7280', fontSize: '0.78rem', lineHeight: 1.5 },

  /* ── CROPS GRID ── */
  cropsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill,minmax(320px,1fr))',
    gap: '1.2rem',
  },
  cropCard: {
    background: '#ffffff',
    border: '1px solid #e5e7eb',
    borderRadius: 18,
    padding: '1.4rem 1.5rem',
    position: 'relative',
    boxShadow: '0 3px 16px rgba(0,0,0,0.06)',
    overflow: 'hidden',
  },
  cropAccent: {
    position: 'absolute', top: 0, left: 0,
    width: 4, bottom: 0, borderRadius: '18px 0 0 18px',
  },

  cropHeader: {
    display: 'flex', alignItems: 'flex-start',
    justifyContent: 'space-between', gap: '1rem',
    marginBottom: '1.1rem', paddingLeft: '0.5rem',
  },
  cropLeft: { display: 'flex', alignItems: 'center', gap: '0.75rem' },
  cropIconBox: {
    width: 42, height: 42, borderRadius: 11, flexShrink: 0,
    display: 'flex', alignItems: 'center',
    justifyContent: 'center', fontSize: '1.3rem',
  },
  cropName: {
    fontSize: '1rem', fontWeight: 800, color: '#14532d',
  },
  cropDesc: { fontSize: '0.74rem', color: '#9ca3af', marginTop: 2 },
  statusBadge: {
    fontSize: '0.62rem', fontWeight: 700,
    letterSpacing: '0.06em', textTransform: 'capitalize',
    padding: '0.28rem 0.8rem', borderRadius: 100, flexShrink: 0,
  },

  /* Metrics */
  metricsRow: {
    display: 'flex', gap: 0,
    background: '#f9fafb',
    border: '1px solid #e5e7eb',
    borderRadius: 12, overflow: 'hidden',
    marginBottom: '0.9rem',
  },
  metricBox: {
    flex: 1, padding: '0.85rem 1rem', textAlign: 'center',
  },
  metricVal: {
    fontSize: '1.05rem', fontWeight: 900,
    color: '#14532d', lineHeight: 1, marginBottom: '0.25rem',
  },
  metricLbl: {
    fontSize: '0.58rem', letterSpacing: '0.08em',
    textTransform: 'uppercase', color: '#9ca3af',
  },
  metricDivider: {
    width: 1, background: '#e5e7eb', flexShrink: 0,
  },

  /* Ratio bar */
  barTrack: {
    height: 6, background: '#e5e7eb',
    borderRadius: 3, overflow: 'hidden',
    marginBottom: '0.3rem',
  },
  barFill: {
    height: '100%', borderRadius: 3,
    transition: 'width 0.6s ease',
  },
  barLabels: {
    display: 'flex', justifyContent: 'space-between',
    fontSize: '0.6rem', color: '#9ca3af',
    marginBottom: '1rem',
  },

  /* Recommendation */
  recBox: {
    background: '#f0fdf4',
    border: '1px solid #bbf7d0',
    borderRadius: 10,
    padding: '0.75rem 1rem',
    display: 'flex', alignItems: 'flex-start',
    gap: '0.55rem', marginBottom: '0.85rem',
  },
  recIcon: { fontSize: '1rem', flexShrink: 0, paddingTop: 1 },
  recText: {
    fontSize: '0.8rem', color: '#14532d',
    lineHeight: 1.6, margin: 0,
  },

  /* Redistribution */
  redistSection: { marginBottom: '0.85rem' },
  redistTitle: {
    fontSize: '0.68rem', fontWeight: 700,
    color: '#6b7280', letterSpacing: '0.08em',
    textTransform: 'uppercase', marginBottom: '0.5rem',
  },
  redistRow: { display: 'flex', flexWrap: 'wrap', gap: '0.5rem' },
  redistPill: {
    background: '#f0fdf4',
    border: '1px solid #bbf7d0',
    borderRadius: 8,
    padding: '0.38rem 0.85rem',
    fontSize: '0.76rem', color: '#15803d',
    display: 'flex', alignItems: 'center', gap: '0.4rem',
  },
  redistArrow: { fontWeight: 900, fontSize: '0.9rem', color: '#16a34a' },

  /* Price impact */
  priceBox: {
    background: '#fffbeb',
    border: '1px solid #fde68a',
    borderLeft: '3px solid #f59e0b',
    borderRadius: 10,
    padding: '0.7rem 1rem',
    display: 'flex', alignItems: 'flex-start', gap: '0.55rem',
  },
  priceIcon: { fontSize: '0.95rem', flexShrink: 0, paddingTop: 1 },
  priceText: {
    fontSize: '0.78rem', color: '#92400e',
    lineHeight: 1.6, margin: 0,
  },

  /* Empty states */
  emptyBox: {
    gridColumn: '1 / -1', textAlign: 'center',
    background: '#fff', border: '1px solid #e5e7eb',
    borderRadius: 18,
    padding: '3rem 2rem',
    boxShadow: '0 2px 10px rgba(0,0,0,0.04)',
  },
  emptyIcon:  { fontSize: '2.8rem', marginBottom: '0.7rem', opacity: 0.4 },
  emptyTitle: { fontSize: '1rem', fontWeight: 700, color: '#374151', marginBottom: '0.3rem' },
  emptySub:   { color: '#9ca3af', fontSize: '0.84rem' },

  emptyState: {
    background: '#fff',
    border: '1.5px dashed #bbf7d0',
    borderRadius: 20,
    padding: '4rem 2rem', textAlign: 'center',
    boxShadow: '0 2px 12px rgba(34,197,94,0.06)',
  },
  emptyStateEmoji: { fontSize: '4rem', marginBottom: '1rem', opacity: 0.45 },
  emptyStateTitle: {
    fontSize: '1.3rem', fontWeight: 800,
    color: '#14532d', marginBottom: '0.5rem',
  },
  emptyStateSub: {
    color: '#6b7280', fontSize: '0.88rem', lineHeight: 1.7,
  },
};