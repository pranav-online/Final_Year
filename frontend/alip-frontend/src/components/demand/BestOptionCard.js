import React from 'react';
import { C, ROI_BAND, button, card, chip, rupees } from './theme';

/* The answer first: the single best place to sell, in plain words, with one action. */
export default function BestOptionCard({ result, commodityName, onDispatch, dispatchingTo }) {
  if (!result || result.error || !result.destinations) return null;
  const qty = Number(result.quantity_kg);
  const best = result.destinations[0];

  if (!best) {
    return (
      <section style={{ ...card, borderLeft: '5px solid #9ca3af' }} aria-label="Best place to sell">
        <h2 style={heading}>No market within 500 km has a recent price</h2>
        <p style={sub}>Try another city, or check again after today's mandi price pull.</p>
      </section>
    );
  }

  const profitable = best.expected_margin > 0;
  const band = ROI_BAND[best.roi_band] || ROI_BAND['Loss-Making'];
  const freightPerKg = best.transport.cost / qty;

  return (
    <section
      aria-label="Best place to sell"
      style={{ ...card, borderLeft: `5px solid ${profitable ? '#22c55e' : '#ef4444'}`,
               background: profitable ? 'linear-gradient(135deg,#ffffff 60%,#f0fdf4)' : '#fff' }}
    >
      <div style={{ fontSize: '0.68rem', fontWeight: 800, letterSpacing: '0.12em', color: C.green, textTransform: 'uppercase' }}>
        {profitable ? 'Best place to sell' : 'No profitable market right now'}
      </div>
      <h2 style={heading}>
        {profitable
          ? <>Sell in {best.destination} — earn <span style={{ color: C.green }}>{rupees(best.expected_margin)}</span> profit</>
          : <>Every market loses money after freight — the closest to break-even is {best.destination}</>}
      </h2>
      <p style={sub}>
        {qty.toLocaleString('en-IN')} kg of {commodityName} bought at {rupees(result.source_price_per_kg, 2)}/kg in {result.source}.
      </p>

      <div style={statsRow}>
        <Stat label="Sells for" value={`${rupees(best.expected_price_per_kg, 2)}/kg`} />
        <Stat label="Freight" value={`− ${rupees(freightPerKg, 2)}/kg`} note={`${best.transport.trucks}× ${best.transport.truck_type} truck · ${best.distance_km} km`} />
        <Stat label="You keep" value={`${rupees(best.net_price_per_kg, 2)}/kg`} strong />
        <Stat label="Return on freight" value={<span style={chip(band.bg, band.color)}>{best.roi}× {best.roi_band}</span>} />
      </div>

      {best.thin_sample && (
        <p role="note" style={warn}>
          ⚠ This price comes from only {best.markets_in_sample} market{best.markets_in_sample === 1 ? '' : 's'} —
          confirm it with a local trader before dispatching.
        </p>
      )}
      {!best.uses_forecast && (
        <p style={{ ...sub, margin: '0.4rem 0 0' }}>
          Based on this week's mandi price (no forecast yet), so prices may move before your truck arrives.
        </p>
      )}

      {profitable && (
        <button
          style={{ ...button, marginTop: '0.9rem', opacity: dispatchingTo ? 0.7 : 1 }}
          disabled={Boolean(dispatchingTo)}
          onClick={() => onDispatch(best)}
        >
          {dispatchingTo === best.destination ? 'Dispatching…' : `🚚 Dispatch to ${best.destination}`}
        </button>
      )}
    </section>
  );
}

function Stat({ label, value, note, strong }) {
  return (
    <div style={{ minWidth: 0 }}>
      <div style={{ fontSize: '0.66rem', letterSpacing: '0.08em', textTransform: 'uppercase', color: C.faint }}>{label}</div>
      <div style={{ fontSize: strong ? '1.25rem' : '1.05rem', fontWeight: 800, color: strong ? C.green : C.ink }}>{value}</div>
      {note && <div style={{ fontSize: '0.7rem', color: C.faint }}>{note}</div>}
    </div>
  );
}

const heading = { margin: '0.3rem 0 0.2rem', fontSize: 'clamp(1.05rem, 2.6vw, 1.4rem)', fontWeight: 900, color: C.ink, lineHeight: 1.3 };
const sub = { margin: 0, color: C.muted, fontSize: '0.85rem' };
const statsRow = {
  display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 140px), 1fr))',
  gap: '0.8rem', margin: '0.9rem 0 0', padding: '0.8rem 0 0', borderTop: '1px dashed #d1e7d1',
};
const warn = {
  margin: '0.8rem 0 0', padding: '0.55rem 0.8rem', borderRadius: 10,
  background: '#fffbeb', border: '1px solid #fde68a', color: '#92400e', fontSize: '0.82rem',
};
