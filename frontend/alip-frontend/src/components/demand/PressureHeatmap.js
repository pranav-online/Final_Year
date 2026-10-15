import React, { useMemo, useState } from 'react';
import { C, COMMODITY_ICON, QUADRANT, card, chip, sectionTitle, titleCase } from './theme';

/* Prices across states for one commodity at a time, coloured by market pressure once it is known. */
export default function PressureHeatmap({ overview, onPick, defaultCommodity }) {
  const rows = useMemo(() => (overview && overview.rows) || [], [overview]);
  const commodities = useMemo(() => [...new Set(rows.map((r) => r.commodity))].sort(), [rows]);
  const [picked, setPicked] = useState(null);
  const commodity = picked || (commodities.includes(defaultCommodity) ? defaultCommodity : commodities[0]);
  if (!overview) return null;

  const states = rows
    .filter((r) => r.commodity === commodity && r.price)
    .sort((a, b) => b.price - a.price);
  const max = Math.max(...states.map((r) => r.price), 1);
  const anyPressure = states.some((r) => r.quadrant && r.quadrant !== 'insufficient_data');

  return (
    <section style={card} aria-label="Prices across states">
      <h3 style={sectionTitle}>Prices across states (₹ per kg)</h3>
      {rows.length === 0 ? (
        <p style={{ margin: 0, color: C.muted, fontSize: '0.85rem' }}>No mandi prices collected yet.</p>
      ) : (
        <>
          <div role="tablist" aria-label="Commodity" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginBottom: '0.8rem' }}>
            {commodities.map((c) => (
              <button key={c} role="tab" aria-selected={c === commodity} onClick={() => setPicked(c)}
                      style={{
                        border: `1.5px solid ${c === commodity ? '#16a34a' : '#d1fae5'}`,
                        background: c === commodity ? '#dcfce7' : '#fff', color: C.ink, borderRadius: 100,
                        padding: '0.3rem 0.8rem', fontSize: '0.78rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit',
                      }}>
                {COMMODITY_ICON[c] || '🌱'} {titleCase(c)}
              </button>
            ))}
          </div>
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: '0.35rem' }}>
            {states.map((r) => {
              const q = QUADRANT[r.quadrant] || QUADRANT.insufficient_data;
              return (
                <li key={r.scope_key}>
                  <button
                    onClick={() => onPick(commodity, r.scope_name)}
                    aria-label={`Analyse ${titleCase(commodity)} in ${r.scope_name}: ₹${(r.price / 100).toFixed(2)} per kg, ${q.label}`}
                    style={{
                      width: '100%', display: 'grid', gridTemplateColumns: 'minmax(90px, 30%) 1fr auto',
                      alignItems: 'center', gap: '0.6rem', background: 'transparent', border: 'none',
                      padding: '0.2rem 0', cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left',
                    }}>
                    <span style={{ fontSize: '0.82rem', color: C.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {r.scope_name}
                    </span>
                    <span style={{ height: 14, background: '#f3f4f6', borderRadius: 7, overflow: 'hidden' }}>
                      <span style={{
                        display: 'block', height: '100%', width: `${(r.price / max) * 100}%`, borderRadius: 7,
                        background: r.quadrant && r.quadrant !== 'insufficient_data' ? q.color : '#86efac',
                      }} />
                    </span>
                    <span style={{ fontSize: '0.82rem', fontWeight: 800, color: C.ink, whiteSpace: 'nowrap' }}>
                      ₹{(r.price / 100).toFixed(2)}
                      {r.quadrant && r.quadrant !== 'insufficient_data' && (
                        <span style={{ ...chip(q.bg, q.color), marginLeft: 6 }}>{q.short}</span>
                      )}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
          <p style={{ margin: '0.7rem 0 0', fontSize: '0.76rem', color: C.muted }}>
            Click a state to analyse it.{' '}
            {anyPressure ? 'Labels show market pressure (glut, shortage…).' : (overview.history_note || '')}
          </p>
        </>
      )}
    </section>
  );
}
