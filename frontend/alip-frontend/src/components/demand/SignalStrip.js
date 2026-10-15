import React from 'react';
import { C, QUADRANT, card, chip, infoDot, pct, perKg, sectionTitle } from './theme';

/* Weeks of weekly prices each signal needs, and a plain-language explanation. */
const METRICS = [
  { key: 'momentum_4w', label: '4-week change', weeks: 5, fmt: pct,
    help: 'How much the price has moved over the last 4 weeks. Rising prices favour holding; falling prices favour selling.' },
  { key: 'volatility_8w', label: 'Price swings', weeks: 6, fmt: (v) => `${(v * 100).toFixed(1)}%/wk`,
    help: 'How much prices jump week to week (last 8 weeks). Higher means riskier to hold stock.' },
  { key: 'price_vs_norm', label: 'vs usual for this week', weeks: 52, fmt: pct,
    help: 'This week\'s price compared with the same week in previous years. Needs a year of history.' },
  { key: 'arrivals_ratio', label: 'Arrivals vs normal', weeks: 5, fmt: (v) => `${v.toFixed(2)}×`, national: true,
    help: 'How much produce is reaching mandis compared with normal (national figure). Above 1.15× often means a glut.' },
  { key: 'price_z', label: 'Unusual move', weeks: 9, fmt: (v) => (Math.abs(v) >= 3 ? `Yes (${v.toFixed(1)})` : `No (${v.toFixed(1)})`),
    help: 'Whether this week\'s price change is far outside the normal range (3 or more = alert).' },
];

function Tile({ label, value, help, sub, ready }) {
  return (
    <div style={{
      minWidth: 0, background: ready ? '#f9fafb' : '#fcfcfd', border: `1px solid ${C.line}`,
      borderRadius: 12, padding: '0.65rem 0.75rem',
    }}>
      <div style={{ fontSize: '0.66rem', letterSpacing: '0.06em', textTransform: 'uppercase', color: C.faint }}>
        {label}
        {help && <span style={infoDot} title={help} aria-label={help} role="img">i</span>}
      </div>
      <div style={{ fontSize: '1.05rem', fontWeight: 800, color: ready ? C.ink : C.faint }}>{value}</div>
      {sub}
    </div>
  );
}

function Progress({ have, need }) {
  const share = Math.min(1, have / need);
  return (
    <div>
      <div style={{ height: 5, background: '#e5e7eb', borderRadius: 3, overflow: 'hidden', margin: '0.3rem 0 0.15rem' }}>
        <div style={{ width: `${share * 100}%`, height: '100%', background: '#86efac' }} />
      </div>
      <div style={{ fontSize: '0.68rem', color: C.faint }}>needs {need} weeks · {Math.min(have, need)}/{need}</div>
    </div>
  );
}

/* Descriptive signals for the analysed area: inferred pressure, momentum, swings, seasonality. */
export default function SignalStrip({ signal, stateName }) {
  if (!signal) {
    return (
      <section style={card} aria-label="Market signals">
        <h3 style={sectionTitle}>Market signals — {stateName}</h3>
        <p style={{ margin: 0, color: C.muted, fontSize: '0.85rem' }}>
          No mandi prices for this commodity in {stateName} yet.
        </p>
      </section>
    );
  }
  const q = QUADRANT[signal.quadrant] || QUADRANT.insufficient_data;
  const weeks = signal.weeks_of_history || 0;

  return (
    <section style={card} aria-label="Market signals">
      <h3 style={{ ...sectionTitle, flexWrap: 'wrap' }}>
        Market signals — {stateName}
        <span style={chip(q.bg, q.color)}
              title="Worked out from how prices move against arrivals; demand itself is never measured directly">
          Market pressure: {q.label}
        </span>
      </h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 140px), 1fr))', gap: '0.6rem' }}>
        <Tile label="Price this week" ready value={perKg(signal.price)}
              help="Median mandi price across reporting markets in this state."
              sub={<div style={{ fontSize: '0.68rem', color: C.faint }}>{signal.markets_reporting || 1} market(s)</div>} />
        {METRICS.map((m) => {
          const v = signal[m.key];
          const ready = v !== null && v !== undefined;
          return (
            <Tile key={m.key} label={m.label} help={m.help} ready={ready}
                  value={ready ? m.fmt(v) : 'Not yet'}
                  sub={ready
                    ? (m.national ? <div style={{ fontSize: '0.68rem', color: C.faint }}>national figure</div> : null)
                    : <Progress have={weeks} need={m.weeks} />} />
          );
        })}
      </div>
      <p style={{ margin: '0.8rem 0 0', fontSize: '0.78rem', color: C.muted }}>
        {signal.seasonal_index_month
          ? `Season: prices this month usually run ${pct(signal.seasonal_index_month - 1)} vs the yearly average` +
            (signal.seasonal_trend ? ` and are ${signal.seasonal_trend === 'rising' ? 'usually higher' : 'usually lower'} next month.` : '.')
          : `Seasonal pattern appears after a full year of prices (${weeks} week${weeks === 1 ? '' : 's'} so far).`}
      </p>
    </section>
  );
}
