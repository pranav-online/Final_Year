import React from 'react';
import { ACTION, C, CONFIDENCE, card, chip, titleCase } from './theme';

/* SELL / HOLD / WATCH with the reason in plain words and an honest confidence label. */
export default function ActionCard({ action, commodity, location }) {
  if (!action) return null;
  const look = ACTION[action.action] || ACTION.WATCH;
  const conf = CONFIDENCE[action.confidence] || CONFIDENCE.insufficient;

  return (
    <section
      aria-label={`Recommended action: ${action.action}`}
      style={{ ...card, borderLeft: `5px solid ${look.border}` }}
    >
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.6rem', marginBottom: '0.6rem' }}>
        <span style={{ ...chip(look.bg, look.color), fontSize: '0.95rem', padding: '0.35rem 0.9rem' }}>
          <span aria-hidden="true">{look.icon} </span>{action.action}
        </span>
        <span style={chip(conf.bg, conf.color)}>{conf.label}</span>
        {action.urgency ? (
          <span style={chip('#f3f4f6', '#374151')}>Urgency {action.urgency}/10</span>
        ) : null}
        <span style={{ fontSize: '0.78rem', color: C.muted }}>
          {titleCase(commodity)} · {location} · act within {action.action_window}
        </span>
      </div>
      <p style={{ margin: 0, color: C.text, fontSize: '0.95rem', lineHeight: 1.55 }}>{action.reason}</p>
      {action.range_text && (
        <p style={{ margin: '0.5rem 0 0', color: C.muted, fontSize: '0.82rem' }}>{action.range_text}</p>
      )}
    </section>
  );
}
