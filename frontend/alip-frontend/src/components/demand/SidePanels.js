import React, { useEffect, useState } from 'react';
import { C, button, card, chip, ghostButton, input, label, rupees, sectionTitle, titleCase } from './theme';

const SEVERITY = {
  high: chip('#fee2e2', '#991b1b'),
  medium: chip('#fef3c7', '#92400e'),
  low: chip('#f3f4f6', '#374151'),
};

/* Farmer listings ranked for this broker (watchlist, radius, margin, seller pressure, truck fill). */
export function MatchesPanel({ matches, needsSettings, onAnalyse }) {
  return (
    <section style={card} aria-label="Matched farmer listings">
      <h3 style={sectionTitle}>Farmer listings for you</h3>
      {needsSettings ? (
        <p style={{ margin: 0, color: C.muted, fontSize: '0.84rem' }}>
          Set your home region in <strong>My trading settings</strong> to see listings near you.
        </p>
      ) : !matches || matches.length === 0 ? (
        <p style={{ margin: 0, color: C.muted, fontSize: '0.84rem' }}>No available listings match your watchlist and radius.</p>
      ) : (
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: '0.6rem' }}>
          {matches.slice(0, 6).map((m) => (
            <li key={m.listing.id} style={{ border: `1px solid ${C.line}`, borderRadius: 10, padding: '0.6rem 0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem', flexWrap: 'wrap' }}>
                <strong style={{ color: C.ink, fontSize: '0.86rem' }}>
                  {Number(m.listing.quantity_kg).toLocaleString('en-IN')} kg {titleCase(m.listing.crop_name)} · {titleCase(m.listing.location)}
                </strong>
                <span style={chip('#dcfce7', '#166534')}>Match {m.score}/100</span>
              </div>
              <div style={{ fontSize: '0.76rem', color: C.muted, margin: '0.25rem 0 0.4rem' }}>
                {rupees(m.listing.price_per_kg, 2)}/kg · {m.distance_km} km
                {m.expected_margin_per_kg !== null ? ` · est. margin ${rupees(m.expected_margin_per_kg, 2)}/kg` : ''}
              </div>
              <button style={ghostButton} onClick={() => onAnalyse(m)}>Analyse this listing</button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/* Latest market-wide alerts plus this broker's own listing matches. */
export function AlertsFeed({ alerts }) {
  return (
    <section style={card} aria-label="Alerts">
      <h3 style={sectionTitle}>Alerts</h3>
      {!alerts || alerts.length === 0 ? (
        <p style={{ margin: 0, color: C.muted, fontSize: '0.84rem' }}>No alerts in the last few days.</p>
      ) : (
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: '0.55rem' }}>
          {alerts.slice(0, 8).map((a) => (
            <li key={a.id} style={{ borderLeft: `3px solid ${C.line}`, paddingLeft: '0.6rem' }}>
              <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', flexWrap: 'wrap' }}>
                <span style={SEVERITY[a.severity] || SEVERITY.low}>{a.severity}</span>
                <strong style={{ fontSize: '0.82rem', color: C.ink }}>{a.title}</strong>
              </div>
              <div style={{ fontSize: '0.76rem', color: C.muted, marginTop: '0.2rem' }}>{a.message}</div>
              <div style={{ fontSize: '0.68rem', color: C.faint }}>{new Date(a.created_at).toLocaleString('en-IN')}</div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

const NEXT = { initiated: ['in_transit', 'cancelled'], in_transit: ['delivered', 'cancelled'] };
const STATUS_LABEL = { in_transit: 'Mark dispatched', delivered: 'Mark delivered', cancelled: 'Cancel' };
const STATUS_CHIP = {
  initiated: chip('#e0f2fe', '#075985'), in_transit: chip('#fef9c3', '#854d0e'),
  delivered: chip('#dcfce7', '#166534'), cancelled: chip('#f3f4f6', '#6b7280'),
};

/* Report §2.10 lifecycle: initiated → in transit → delivered (cancel before delivery). */
export function ShipmentsPanel({ shipments, onChange, busyId }) {
  return (
    <section style={card} aria-label="Shipments">
      <h3 style={sectionTitle}>My shipments</h3>
      {!shipments || shipments.length === 0 ? (
        <p style={{ margin: 0, color: C.muted, fontSize: '0.84rem' }}>No shipments yet. Use Dispatch in “Where to sell”.</p>
      ) : (
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: '0.6rem' }}>
          {shipments.slice(0, 8).map((s) => (
            <li key={s.id} style={{ border: `1px solid ${C.line}`, borderRadius: 10, padding: '0.6rem 0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem', flexWrap: 'wrap' }}>
                <strong style={{ fontSize: '0.84rem', color: C.ink }}>
                  {Number(s.quantity_kg).toLocaleString('en-IN')} kg {titleCase(s.commodity)}: {s.source_region} → {s.destination_region}
                </strong>
                <span style={STATUS_CHIP[s.status]}>{s.status.replace('_', ' ')}</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: C.muted, margin: '0.25rem 0 0.4rem' }}>
                {s.trucks}× {s.truck_type} · {s.distance_km} km · freight {rupees(s.transport_cost)}
                {s.roi !== null ? ` · ROI ${s.roi}× ${s.roi_band}` : ''}
              </div>
              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                {(NEXT[s.status] || []).map((next) => (
                  <button key={next} style={ghostButton} disabled={busyId === s.id} onClick={() => onChange(s, next)}>
                    {STATUS_LABEL[next]}
                  </button>
                ))}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/* Home region, watchlist, radius, truck, rates and commission used by matching and ranking. */
export function SettingsPanel({ settings, regions, commodities, onSave, saving }) {
  const [draft, setDraft] = useState(settings);
  useEffect(() => { setDraft(settings); }, [settings]);
  if (!draft) return null;
  const set = (key, value) => setDraft((d) => ({ ...d, [key]: value }));
  const toggle = (id) => set('watch_commodities', draft.watch_commodities.includes(id)
    ? draft.watch_commodities.filter((c) => c !== id)
    : [...draft.watch_commodities, id]);

  return (
    <details style={card}>
      <summary style={{ ...sectionTitle, margin: 0, cursor: 'pointer' }}>My trading settings</summary>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: '0.8rem', marginTop: '0.9rem' }}>
        <div>
          <label style={label} htmlFor="home-region">Home region</label>
          <select id="home-region" style={input} value={draft.home_region || ''} onChange={(e) => set('home_region', e.target.value || null)}>
            <option value="">— choose —</option>
            {regions.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <div>
          <label style={label} htmlFor="radius">Radius (km)</label>
          <input id="radius" style={input} type="number" min="10" max="1000" value={draft.radius_km}
                 onChange={(e) => set('radius_km', Number(e.target.value))} />
        </div>
        <div>
          <label style={label} htmlFor="truck">Truck</label>
          <select id="truck" style={input} value={draft.truck_type || ''} onChange={(e) => set('truck_type', e.target.value || null)}>
            <option value="">Cheapest that fits</option>
            <option value="small">Small · 3 t · ₹25/km</option>
            <option value="medium">Medium · 10 t · ₹35/km</option>
            <option value="large">Large · 20 t · ₹50/km</option>
          </select>
        </div>
        <div>
          <label style={label} htmlFor="commission">Commission + fees (%)</label>
          <input id="commission" style={input} type="number" min="0" max="20" step="0.5" value={draft.commission_pct}
                 onChange={(e) => set('commission_pct', Number(e.target.value))} />
        </div>
      </div>
      <fieldset style={{ border: 'none', padding: 0, margin: '0.9rem 0 0' }}>
        <legend style={label}>Watchlist (none ticked = all)</legend>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
          {commodities.map((c) => (
            <label key={c.id} style={{ fontSize: '0.8rem', color: C.text, display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <input type="checkbox" checked={draft.watch_commodities.includes(c.id)} onChange={() => toggle(c.id)} />
              {c.name}
            </label>
          ))}
        </div>
      </fieldset>
      <button style={{ ...button, marginTop: '0.9rem', opacity: saving ? 0.7 : 1 }} disabled={saving} onClick={() => onSave(draft)}>
        {saving ? 'Saving…' : 'Save settings'}
      </button>
    </details>
  );
}
