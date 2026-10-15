import React from 'react';
import {
  Area, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { C, card, rupees, sectionTitle } from './theme';

export const MIN_TREND_POINTS = 4;

const kg = (perQuintal) => (perQuintal === null || perQuintal === undefined ? undefined : Math.round(perQuintal) / 100);

export const weekLabel = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });

/* Merge weekly history with the forecast fan, in Rs per kg, so the fan starts at today's price. */
export function buildFanData(history = [], horizons = []) {
  const rows = history.map((w) => ({ week: w.week_start, price: kg(w.modal_price) }));
  if (rows.length && horizons.length) {
    const last = rows[rows.length - 1];
    last.p50 = last.price;
    last.band = [last.price, last.price];
    horizons.forEach((h) => rows.push({ week: h.target_week, p50: kg(h.p50), band: [kg(h.p10), kg(h.p90)] }));
  }
  return rows;
}

function TrendTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  const row = payload[0].payload;
  return (
    <div style={{ background: '#fff', border: `1px solid ${C.line}`, borderRadius: 10, padding: '0.55rem 0.75rem', fontSize: '0.8rem', boxShadow: '0 4px 14px rgba(0,0,0,0.08)' }}>
      <strong style={{ color: C.ink }}>Week of {weekLabel(label)}</strong>
      {row.price !== undefined && <div>Mandi price {rupees(row.price, 2)}/kg ({rupees(row.price * 100)}/quintal)</div>}
      {row.band && row.price === undefined && (
        <>
          <div>Most likely {rupees(row.p50, 2)}/kg</div>
          <div>8 in 10 times between {rupees(row.band[0], 2)} and {rupees(row.band[1], 2)}/kg</div>
        </>
      )}
    </div>
  );
}

function Chart({ data, today, breakEven, hasForecast, width, height }) {
  return (
    <ComposedChart data={data} width={width} height={height} margin={{ top: 22, right: 16, bottom: 0, left: 0 }}>
      <defs>
        <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#22c55e" stopOpacity={0.28} />
          <stop offset="100%" stopColor="#22c55e" stopOpacity={0.02} />
        </linearGradient>
      </defs>
      <CartesianGrid stroke="#f0f0f0" vertical={false} />
      <XAxis dataKey="week" tick={{ fontSize: 11 }} tickFormatter={weekLabel} minTickGap={16} />
      <YAxis tick={{ fontSize: 11 }} width={52} tickFormatter={(v) => `₹${v}`} domain={['auto', 'auto']} />
      <Tooltip content={<TrendTooltip />} />
      <Legend wrapperStyle={{ fontSize: 12 }} />
      {hasForecast && <Area dataKey="band" name="Likely range (8 in 10)" fill="#bbf7d0" stroke="none" isAnimationActive={false} />}
      <Area dataKey="price" name="Weekly mandi price" stroke={C.ink} strokeWidth={2.5} fill="url(#priceFill)"
            dot={{ r: 3, fill: C.ink }} activeDot={{ r: 5 }} isAnimationActive={false} connectNulls />
      {hasForecast && <Line dataKey="p50" name="Forecast (most likely)" stroke={C.green} strokeDasharray="6 4" strokeWidth={2.5} dot isAnimationActive={false} />}
      {today && <ReferenceLine x={today} stroke="#374151" strokeDasharray="3 3" label={{ value: 'Today', fontSize: 11, position: 'top' }} />}
      {breakEven && <ReferenceLine x={breakEven} stroke="#ef4444" strokeDasharray="4 4" label={{ value: 'Break-even', fontSize: 11, position: 'top' }} />}
    </ComposedChart>
  );
}

/* Price trend (Rs/kg) with the forecast fan; until enough weeks exist, shows collection progress instead of a lone dot. */
export default function FanChart({ history = [], forecast, breakEvenWeek, width, placeName }) {
  const horizons = forecast && forecast.confidence !== 'insufficient' ? forecast.horizons || [] : [];
  const data = buildFanData(history, horizons);
  const today = history.length ? history[history.length - 1].week_start : null;
  const latest = history.length ? history[history.length - 1] : null;
  const enough = history.length >= MIN_TREND_POINTS;
  const summary = horizons.length
    ? `Weekly prices with a forecast range for the next ${horizons[horizons.length - 1].h_weeks} weeks`
    : 'Weekly mandi prices';

  return (
    <section style={card} aria-label="Price history and forecast">
      <h3 style={sectionTitle}>Price trend{placeName ? ` — ${placeName}` : ''} (₹ per kg)</h3>

      {!history.length ? (
        <p style={{ color: C.muted, fontSize: '0.85rem', margin: 0 }}>No weekly price history yet.</p>
      ) : !enough ? (
        <div>
          <div style={{ fontSize: '0.72rem', color: C.faint, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            This week (from {weekLabel(latest.week_start)})
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 900, color: C.ink }}>
            {rupees(latest.modal_price / 100, 2)}<span style={{ fontSize: '0.9rem', color: C.muted }}>/kg</span>
          </div>
          <div style={{ fontSize: '0.78rem', color: C.muted, marginBottom: '0.9rem' }}>
            {rupees(latest.modal_price)}/quintal · {latest.markets} market(s) reporting
          </div>
          <div aria-label={`${history.length} of ${MIN_TREND_POINTS} weeks collected`}
               style={{ height: 8, background: '#e5e7eb', borderRadius: 4, overflow: 'hidden' }}>
            <div style={{ width: `${(history.length / MIN_TREND_POINTS) * 100}%`, height: '100%', background: '#22c55e' }} />
          </div>
          <p style={{ margin: '0.5rem 0 0', fontSize: '0.8rem', color: C.muted }}>
            The trend chart appears after {MIN_TREND_POINTS} weeks of prices — {history.length} of {MIN_TREND_POINTS} collected.
            Prices are pulled automatically every afternoon and evening.
          </p>
        </div>
      ) : (
        <div role="img" aria-label={summary} style={{ width: '100%', height: 280 }}>
          {width ? (
            <Chart data={data} today={today} breakEven={breakEvenWeek} hasForecast={horizons.length > 0} width={width} height={280} />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <Chart data={data} today={today} breakEven={breakEvenWeek} hasForecast={horizons.length > 0} />
            </ResponsiveContainer>
          )}
        </div>
      )}

      {history.length > 0 && !horizons.length && (
        <p style={{ margin: '0.7rem 0 0', fontSize: '0.78rem', color: C.muted }}>
          <strong>Not enough signal</strong> for a forecast yet
          {forecast && forecast.reason ? ` (${forecast.reason})` : ''}. A forecast is shown only once it has proven
          more accurate than simple guesses on past data.
        </p>
      )}
    </section>
  );
}
