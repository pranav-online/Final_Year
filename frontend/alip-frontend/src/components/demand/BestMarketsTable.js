import React from 'react';
import { C, ROI_BAND, card, chip, ghostButton, rupees, sectionTitle } from './theme';

const th = {
  textAlign: 'left', padding: '0.5rem 0.6rem', fontSize: '0.66rem', letterSpacing: '0.06em',
  textTransform: 'uppercase', color: C.faint, borderBottom: `1px solid ${C.line}`, whiteSpace: 'nowrap',
};
const td = { padding: '0.55rem 0.6rem', fontSize: '0.82rem', color: C.text, borderBottom: `1px solid ${C.line}`, verticalAlign: 'top' };

/* Destinations ranked by expected margin after freight (report §2.6 ROI) with a dispatch action. */
export default function BestMarketsTable({ result, onDispatch, dispatchingTo, bare = false }) {
  if (!result) return null;
  // `bare`: rendered inside another card (e.g. a "full breakdown" disclosure), so no card or title.
  const wrap = bare ? {} : card;
  if (result.error) {
    return (
      <section style={wrap} aria-label="Best markets">
        {!bare && <h3 style={sectionTitle}>Where to sell</h3>}
        <p style={{ margin: 0, color: C.muted, fontSize: '0.85rem' }}>{result.error}</p>
      </section>
    );
  }
  const rows = result.destinations || [];

  return (
    <section style={wrap} aria-label="Best markets">
      {!bare && (
        <h3 style={sectionTitle}>
          Where to sell {Number(result.quantity_kg).toLocaleString('en-IN')} kg from {result.source}
        </h3>
      )}
      <p style={{ margin: '-0.4rem 0 0.8rem', fontSize: '0.78rem', color: C.muted }}>
        Bought at {rupees(result.source_price_per_kg, 2)}/kg ({result.source_price_basis}). Net price is after freight
        {result.settings_used && result.settings_used.commission_pct ? ` and ${result.settings_used.commission_pct}% commission` : ''}.
      </p>
      {rows.length === 0 ? (
        <p style={{ margin: 0, color: C.muted, fontSize: '0.85rem' }}>
          No destination within 500 km has recent prices for this commodity.
        </p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 720 }}>
            <thead>
              <tr>
                {['Destination', 'Distance', 'Expected price', 'Freight', 'Net / kg', 'Margin', 'ROI', 'Break-even', ''].map((h) => (
                  <th key={h} style={th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((d) => {
                const band = ROI_BAND[d.roi_band] || ROI_BAND['Loss-Making'];
                return (
                  <tr key={d.destination}>
                    <td style={td}>
                      <strong>{d.destination}</strong>
                      <div style={{ fontSize: '0.7rem', color: C.faint }}>{d.state}</div>
                    </td>
                    <td style={td}>{d.distance_km} km</td>
                    <td style={td}>
                      {rupees(d.expected_price_per_kg, 2)}/kg
                      {d.downside_price_per_kg !== null && (
                        <div style={{ fontSize: '0.7rem', color: C.faint }}>downside {rupees(d.downside_price_per_kg, 2)}</div>
                      )}
                      <div style={{ fontSize: '0.7rem', color: C.faint }}>
                        {d.uses_forecast ? 'forecast' : 'latest price'} · {d.price_basis}
                      </div>
                      {d.thin_sample && (
                        <span style={chip('#fef3c7', '#92400e')} title="Fewer than 3 markets reported this price">
                          ⚠ thin sample ({d.markets_in_sample})
                        </span>
                      )}
                    </td>
                    <td style={td}>
                      {rupees(d.transport.cost)}
                      <div style={{ fontSize: '0.7rem', color: C.faint }}>
                        {d.transport.trucks}× {d.transport.truck_type} truck
                      </div>
                    </td>
                    <td style={td}><strong>{rupees(d.net_price_per_kg, 2)}</strong></td>
                    <td style={{ ...td, color: d.expected_margin < 0 ? '#991b1b' : C.ink, fontWeight: 700 }}>
                      {rupees(d.expected_margin)}
                    </td>
                    <td style={td}>
                      <span style={chip(band.bg, band.color)}>{d.roi ?? '—'}× {d.roi_band}</span>
                      {d.roi_p10_band && (
                        <div style={{ fontSize: '0.7rem', color: C.faint }}>downside {d.roi_p10}× {d.roi_p10_band}</div>
                      )}
                    </td>
                    <td style={td}>
                      {d.break_even && d.break_even.week ? `week ${d.break_even.week}` : '—'}
                      <div style={{ fontSize: '0.68rem', color: C.faint }}>{d.break_even ? d.break_even.reason : ''}</div>
                    </td>
                    <td style={td}>
                      <button
                        style={{ ...ghostButton, opacity: dispatchingTo ? 0.6 : 1 }}
                        disabled={Boolean(dispatchingTo)}
                        onClick={() => onDispatch(d)}
                        aria-label={`Dispatch to ${d.destination}`}
                      >
                        {dispatchingTo === d.destination ? 'Dispatching…' : 'Dispatch'}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <p style={{ margin: '0.7rem 0 0', fontSize: '0.72rem', color: C.faint }}>
        {(result.notes || []).join(' ')} Inactive ranking factors: {Object.keys(result.inactive_factors || {}).join(', ')}.
      </p>
    </section>
  );
}
