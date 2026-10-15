import React from 'react';
import {
  Bar, BarChart, CartesianGrid, Cell, LabelList, Legend, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { C, card, rupees, sectionTitle } from './theme';

/* One bar per destination: what you keep per kg, plus what freight (and commission) takes. */
export function buildCompareData(result) {
  const qty = Number(result.quantity_kg);
  return (result.destinations || []).map((d) => {
    const freight = d.transport.cost / qty;
    const commission = Math.max(0, d.expected_price_per_kg - freight - d.net_price_per_kg);
    return {
      name: `${d.thin_sample ? '⚠ ' : ''}${d.destination}`,
      destination: d.destination,
      keep: Math.max(0, Number(d.net_price_per_kg.toFixed(2))),
      freight: Number(freight.toFixed(2)),
      commission: Number(commission.toFixed(2)),
      price: d.expected_price_per_kg,
      margin: d.expected_margin,
      profitable: d.expected_margin > 0,
      thin: d.thin_sample,
      distance: d.distance_km,
      roi: d.roi,
      band: d.roi_band,
    };
  });
}

function CompareTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const d = payload[0].payload;
  return (
    <div style={{ background: '#fff', border: `1px solid ${C.line}`, borderRadius: 10, padding: '0.6rem 0.75rem', fontSize: '0.8rem', boxShadow: '0 4px 14px rgba(0,0,0,0.08)' }}>
      <strong style={{ color: C.ink }}>{d.destination}</strong> · {d.distance} km
      <div>Sells for {rupees(d.price, 2)}/kg</div>
      <div>Freight {rupees(d.freight, 2)}/kg{d.commission ? ` · commission ${rupees(d.commission, 2)}/kg` : ''}</div>
      <div style={{ fontWeight: 700, color: d.profitable ? C.green : '#b91c1c' }}>
        You keep {rupees(d.keep, 2)}/kg → {d.profitable ? 'profit' : 'loss'} {rupees(Math.abs(d.margin))}
      </div>
      <div>ROI {d.roi}× ({d.band}){d.thin ? ' · ⚠ thin sample' : ''}</div>
    </div>
  );
}

function Chart({ data, buyPrice, width, height }) {
  return (
    <BarChart data={data} layout="vertical" width={width} height={height}
              margin={{ top: 18, right: 40, bottom: 4, left: 8 }} barCategoryGap={8}>
      <CartesianGrid stroke="#f0f0f0" horizontal={false} />
      <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${v}`} />
      <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 12 }} />
      <Tooltip content={<CompareTooltip />} cursor={{ fill: '#f9fafb' }} />
      <Legend wrapperStyle={{ fontSize: 12 }} />
      <Bar dataKey="keep" name="You keep (₹/kg)" stackId="p" isAnimationActive={false}>
        {data.map((d) => (
          <Cell key={d.destination} fill={d.profitable ? (d.thin ? '#86efac' : '#22c55e') : '#fca5a5'} />
        ))}
      </Bar>
      <Bar dataKey="freight" name="Freight (₹/kg)" stackId="p" fill="#cbd5e1" isAnimationActive={false} />
      <Bar dataKey="commission" name="Commission (₹/kg)" stackId="p" fill="#e2e8f0" isAnimationActive={false}>
        <LabelList dataKey="price" position="right" formatter={(v) => `₹${v}`} style={{ fontSize: 11, fill: C.muted }} />
      </Bar>
      <ReferenceLine x={buyPrice} stroke="#ef4444" strokeDasharray="5 4" strokeWidth={2}
                     label={{ value: `You paid ₹${buyPrice}`, position: 'top', fontSize: 11, fill: '#b91c1c' }} />
    </BarChart>
  );
}

/* Visual answer to "where should I sell?": anything whose green bar passes the red line makes money. */
export default function MarketCompareChart({ result, width }) {
  if (!result || result.error || !(result.destinations || []).length) return null;
  const data = buildCompareData(result);
  const buy = Number(result.source_price_per_kg);
  const height = 70 + data.length * 44;
  const winners = data.filter((d) => d.profitable).length;

  return (
    <section style={card} aria-label="Compare markets">
      <h3 style={sectionTitle}>Compare markets (₹ per kg)</h3>
      <p style={{ margin: '-0.4rem 0 0.6rem', fontSize: '0.8rem', color: C.muted }}>
        Green is what you keep after freight. Bars that pass the red line make a profit —
        {' '}{winners} of {data.length} do. ⚠ marks prices from fewer than 3 markets.
      </p>
      <div role="img" aria-label={`Net price per kg for ${data.length} markets compared with your buy price of ₹${buy}`}
           style={{ width: '100%', height }}>
        {width ? <Chart data={data} buyPrice={buy} width={width} height={height} /> : (
          <ResponsiveContainer width="100%" height="100%">
            <Chart data={data} buyPrice={buy} />
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}
