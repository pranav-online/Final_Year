import React from 'react';
import { C, chip } from './theme';

/* "Prices as of …" so a broker always knows how old the data behind a decision is. */
export default function FreshnessBadge({ freshness }) {
  if (!freshness) return null;
  const { last_price_pull_at: pulledAt, price_week: week, markets_reporting: markets, stale } = freshness;
  const when = pulledAt ? new Date(pulledAt).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : null;

  return (
    <div
      role="status"
      aria-label="Data freshness"
      style={{
        display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.5rem',
        fontSize: '0.78rem', color: C.muted, margin: '0 0 1rem',
      }}
    >
      <span style={stale ? chip('#fef3c7', '#92400e') : chip('#dcfce7', '#166534')}>
        {stale ? '⚠ Stale data' : '● Fresh data'}
      </span>
      <span>
        {when ? `Mandi prices pulled ${when}` : 'No mandi price pull recorded yet'}
        {week ? ` · price week of ${week}` : ''}
        {markets ? ` · ${markets} market(s) reporting` : ''}
      </span>
    </div>
  );
}
