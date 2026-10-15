import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  getAllRegions, getBrokerSettings, getCommodityAnalysis, getDemandAlerts, getDemandOverview,
  getListingMatches, getPriceCommodities, getPriceHistory, getShipments, initiateShipment,
  saveBrokerSettings, updateShipmentStatus,
} from '../services/api';
import ActionCard from '../components/demand/ActionCard';
import BestMarketsTable from '../components/demand/BestMarketsTable';
import BestOptionCard from '../components/demand/BestOptionCard';
import MarketCompareChart from '../components/demand/MarketCompareChart';
import FanChart from '../components/demand/FanChart';
import FreshnessBadge from '../components/demand/FreshnessBadge';
import PressureHeatmap from '../components/demand/PressureHeatmap';
import SignalStrip from '../components/demand/SignalStrip';
import { AlertsFeed, MatchesPanel, SettingsPanel, ShipmentsPanel } from '../components/demand/SidePanels';
import { C, COMMODITY_ICON, button, card, ghostButton, input, label, titleCase } from '../components/demand/theme';

const QUICK_PLACES = ['Guntur', 'Hyderabad', 'Vijayawada', 'Bangalore', 'Pune', 'Chennai'];
const skeleton = { background: 'linear-gradient(90deg,#f3f4f6 25%,#e5e7eb 50%,#f3f4f6 75%)', border: 'none' };

/* ═══════════════════════════════════════════════════════════════
   ALIP — Demand Analysis (Broker)
   Real mandi prices -> inferred pressure, gated forecasts and
   where-to-sell decisions. Nothing on this page is invented.
═══════════════════════════════════════════════════════════════ */

const FALLBACK_COMMODITIES = [
  'tomato', 'banana', 'onion', 'potato', 'maize', 'paddy', 'rice', 'wheat', 'cotton', 'groundnut',
].map((id) => ({ id, name: titleCase(id) }));

const grid = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 320px), 1fr))', gap: '1rem' };

export function errorText(err, fallback) {
  const detail = err && err.response && err.response.data && err.response.data.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length) return detail.map((d) => d.msg).join('; ');
  return fallback;
}

export default function DemandAnalysis() {
  const navigate = useNavigate();
  const [commodities, setCommodities] = useState(FALLBACK_COMMODITIES);
  const [regions, setRegions] = useState([]);
  const [form, setForm] = useState({ commodity: 'tomato', location: '', qty: '', price: '' });
  const [listingId, setListingId] = useState(null);

  const [analysis, setAnalysis] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [overview, setOverview] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [shipments, setShipments] = useState([]);
  const [matches, setMatches] = useState(null);
  const [settings, setSettings] = useState(null);
  const [savingSettings, setSavingSettings] = useState(false);
  const [dispatchingTo, setDispatchingTo] = useState(null);
  const [busyShipment, setBusyShipment] = useState(null);

  const refreshMatches = useCallback(async (current) => {
    if (!current || !current.home_region) { setMatches(null); return; }
    try { setMatches((await getListingMatches()).data.matches); } catch { setMatches([]); }
  }, []);

  const refreshShipments = useCallback(async () => {
    try { setShipments((await getShipments()).data.shipments); } catch { /* panel stays as is */ }
  }, []);

  useEffect(() => {
    (async () => {
      const [c, r, s, o, a] = await Promise.allSettled([
        getPriceCommodities(), getAllRegions(), getBrokerSettings(), getDemandOverview('state'), getDemandAlerts(),
      ]);
      if (c.status === 'fulfilled') setCommodities(c.value.data.commodities);
      if (r.status === 'fulfilled') setRegions(r.value.data.regions);
      if (o.status === 'fulfilled') setOverview(o.value.data);
      if (a.status === 'fulfilled') setAlerts(a.value.data.alerts);
      if (s.status === 'fulfilled') {
        setSettings(s.value.data.settings);
        refreshMatches(s.value.data.settings);
      }
      refreshShipments();
    })();
  }, [refreshMatches, refreshShipments]);

  const analyse = async (next = form) => {
    if (!next.location.trim()) { toast.error('Enter a city or state'); return; }
    setLoading(true);
    setError(null);
    try {
      const res = await getCommodityAnalysis(next.commodity, next.location.trim(), {
        qtyKg: Number(next.qty) || undefined, pricePerKg: Number(next.price) || undefined,
      });
      setAnalysis(res.data);
      try {
        const h = await getPriceHistory(next.commodity, { state: res.data.state, weeks: 26 });
        setHistory(h.data.series);
      } catch { setHistory([]); }
    } catch (err) {
      setAnalysis(null);
      setError(errorText(err, 'Analysis failed. Is the backend running?'));
    }
    setLoading(false);
  };

  const pickFromHeatmap = (commodity, state) => {
    const next = { ...form, commodity, location: state };
    setForm(next);
    setListingId(null);
    analyse(next);
  };

  const analyseListing = (m) => {
    const next = {
      commodity: m.commodity, location: titleCase(m.listing.location),
      qty: String(m.listing.quantity_kg), price: String(m.listing.price_per_kg),
    };
    setForm(next);
    setListingId(m.listing.id);
    analyse(next);
  };

  const dispatch = async (dest) => {
    const qty = Number(form.qty);
    const msg = `Dispatch ${qty.toLocaleString('en-IN')} kg ${titleCase(form.commodity)} from ${analysis.location} to ` +
      `${dest.destination} by ${dest.transport.trucks}× ${dest.transport.truck_type} truck (freight ₹${dest.transport.cost})?`;
    if (!window.confirm(msg)) return;
    setDispatchingTo(dest.destination);
    try {
      await initiateShipment({
        crop: form.commodity, source_region: analysis.location, destination_region: dest.destination,
        quantity_kg: qty, truck_type: dest.transport.truck_type, listing_id: listingId || undefined,
        agreed_price_per_kg: dest.expected_price_per_kg, source_price_per_kg: dest.source_price_per_kg,
      });
      toast.success(`Shipment to ${dest.destination} initiated`);
      setListingId(null);
      refreshShipments();
      refreshMatches(settings);
    } catch (err) {
      toast.error(errorText(err, 'Could not initiate the shipment'));
    }
    setDispatchingTo(null);
  };

  const changeShipment = async (shipment, status) => {
    setBusyShipment(shipment.id);
    try {
      await updateShipmentStatus(shipment.id, status);
      refreshShipments();
    } catch (err) {
      toast.error(errorText(err, 'Status change failed'));
    }
    setBusyShipment(null);
  };

  const saveSettings = async (draft) => {
    setSavingSettings(true);
    try {
      const res = await saveBrokerSettings({
        home_region: draft.home_region, watch_commodities: draft.watch_commodities,
        radius_km: draft.radius_km, truck_type: draft.truck_type, truck_rates: draft.truck_rates || {},
        commission_pct: draft.commission_pct, road_factor: draft.road_factor,
      });
      setSettings(res.data.settings);
      refreshMatches(res.data.settings);
      toast.success('Settings saved');
    } catch (err) {
      toast.error(errorText(err, 'Could not save settings'));
    }
    setSavingSettings(false);
  };

  const field = (key) => ({ value: form[key], onChange: (e) => setForm({ ...form, [key]: e.target.value }) });
  const breakEvenWeek = analysis && analysis.best_markets && analysis.best_markets.destinations
    && analysis.best_markets.destinations[0] && analysis.best_markets.destinations[0].break_even
    ? analysis.best_markets.destinations[0].break_even.target_week : null;

  return (
    <div style={s.page}>
      <header style={s.header}>
        <div style={s.headerInner}>
          <div style={s.logo}>🌿 ALIP<span style={{ color: '#84cc16' }}>.</span></div>
          <h1 style={s.title}>📊 Demand Analysis</h1>
          <button style={s.back} onClick={() => navigate('/broker')}>← Dashboard</button>
        </div>
      </header>

      <main style={s.body}>
        {/* ── Inputs ── */}
        <section style={{ ...card, marginBottom: '1rem' }} aria-label="Analyse a commodity">
          <h2 style={{ margin: '0 0 0.2rem', fontSize: '1.15rem', fontWeight: 900, color: C.ink }}>
            Where should I sell, and should I sell now?
          </h2>
          <p style={{ margin: '0 0 1rem', fontSize: '0.84rem', color: C.muted }}>
            Enter what you have and where it is. We compare live mandi prices within 500 km, minus truck freight.
          </p>
          <form
            onSubmit={(e) => { e.preventDefault(); analyse(); }}
            style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 150px), 1fr))', gap: '0.8rem', alignItems: 'end' }}
          >
            <div>
              <label style={label} htmlFor="commodity">1 · Crop</label>
              <select id="commodity" style={input} {...field('commodity')}>
                {commodities.map((c) => <option key={c.id} value={c.id}>{COMMODITY_ICON[c.id] || '🌱'} {c.name}</option>)}
              </select>
            </div>
            <div>
              <label style={label} htmlFor="location">2 · Where is it now?</label>
              <input id="location" style={input} list="region-list" placeholder="City or state, e.g. Guntur" {...field('location')} />
              <datalist id="region-list">{regions.map((r) => <option key={r} value={r} />)}</datalist>
            </div>
            <div>
              <label style={label} htmlFor="qty">3 · Quantity (kg)</label>
              <input id="qty" style={input} type="number" min="1" placeholder="e.g. 1000" {...field('qty')} />
            </div>
            <div>
              <label style={label} htmlFor="price">4 · You paid (₹/kg)</label>
              <input id="price" style={input} type="number" min="0" step="0.5" placeholder="e.g. 10" {...field('price')} />
            </div>
            <button type="submit" style={{ ...button, opacity: loading ? 0.7 : 1, padding: '0.7rem 1.2rem' }} disabled={loading}>
              {loading ? 'Analysing…' : 'Analyse'}
            </button>
          </form>
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.4rem', marginTop: '0.8rem' }}>
            <span style={{ fontSize: '0.74rem', color: C.faint }}>Quick pick:</span>
            {QUICK_PLACES.filter((p) => !regions.length || regions.includes(p)).map((p) => (
              <button key={p} type="button" style={ghostButton} onClick={() => setForm({ ...form, location: p })}>
                📍 {p}
              </button>
            ))}
          </div>
          <details style={{ marginTop: '0.8rem' }}>
            <summary style={{ cursor: 'pointer', fontSize: '0.8rem', fontWeight: 700, color: C.green }}>How to use this page</summary>
            <ol style={{ margin: '0.5rem 0 0', paddingLeft: '1.2rem', fontSize: '0.82rem', color: C.muted, lineHeight: 1.7 }}>
              <li>Fill all four boxes and press <strong>Analyse</strong>. Quantity and price are needed for the profit comparison.</li>
              <li>Read <strong>Best place to sell</strong> first, then the <strong>Compare markets</strong> chart: green bars that cross the red line make a profit.</li>
              <li><strong>Sell now or hold?</strong> uses price trends; it says “Not enough signal” until a few weeks of prices are collected.</li>
              <li>Press <strong>Dispatch</strong> to book the truck, then track it under <strong>My shipments</strong>.</li>
              <li>Set your home region in <strong>My trading settings</strong> to get alerts when farmers near you list produce.</li>
            </ol>
          </details>
        </section>

        {error && (
          <div role="alert" style={{ ...card, borderLeft: '5px solid #ef4444', marginBottom: '1rem', color: '#991b1b' }}>
            {error}
          </div>
        )}

        {loading && !analysis && (
          <div style={{ display: 'grid', gap: '1rem', marginBottom: '1rem' }} aria-busy="true">
            <span style={{ position: 'absolute', left: -9999 }}>Loading analysis…</span>
            {[120, 260, 200].map((h) => <div key={h} style={{ ...card, height: h, ...skeleton }} />)}
          </div>
        )}

        {/* ── Analysis ── */}
        {analysis ? (
          <div style={{ display: 'grid', gap: '1rem', marginBottom: '1rem', opacity: loading ? 0.55 : 1 }}>
            <FreshnessBadge freshness={analysis.freshness} />
            {analysis.best_markets ? (
              <BestOptionCard result={analysis.best_markets} commodityName={analysis.commodity_name}
                              onDispatch={dispatch} dispatchingTo={dispatchingTo} />
            ) : (
              <div style={{ ...card, borderLeft: '5px solid #93c5fd', color: C.muted, fontSize: '0.88rem' }}>
                💡 Add a <strong>quantity</strong> and what you <strong>paid per kg</strong> to see the best place to sell after freight.
              </div>
            )}
            <ActionCard action={analysis.action} commodity={analysis.commodity_name} location={analysis.location} />
            {analysis.best_markets && <MarketCompareChart result={analysis.best_markets} />}
            <div style={grid}>
              <FanChart history={history} forecast={analysis.forecast} breakEvenWeek={breakEvenWeek} placeName={analysis.state} />
              <SignalStrip signal={analysis.signal} stateName={analysis.state} />
            </div>
            {analysis.best_markets && !analysis.best_markets.error && (
              <details style={card}>
                <summary style={{ cursor: 'pointer', fontWeight: 800, color: C.ink, fontSize: '0.9rem' }}>
                  Show full breakdown (distance, truck, ROI, break-even for each market)
                </summary>
                <div style={{ marginTop: '0.8rem' }}>
                  <BestMarketsTable result={analysis.best_markets} onDispatch={dispatch} dispatchingTo={dispatchingTo} bare />
                </div>
              </details>
            )}
            <p style={{ margin: 0, fontSize: '0.78rem', color: C.muted }}>
              🧑‍🌾 ALIP farmer listings in {analysis.state}: {analysis.listed_supply_in_state.listings} listing(s),{' '}
              {analysis.listed_supply_in_state.quantity_kg.toLocaleString('en-IN')} kg — supply that has not reached a mandi yet.
            </p>
          </div>
        ) : !loading && !error && (
          <div style={{ ...card, marginBottom: '1rem', textAlign: 'center', color: C.muted, border: '1.5px dashed #bbf7d0', padding: '2rem 1rem' }}>
            <div style={{ fontSize: '2rem' }} aria-hidden="true">📊</div>
            Fill in the four boxes above and press <strong>Analyse</strong> — or click a state in “Prices across states” below.
          </div>
        )}

        {/* ── Market-wide ── */}
        <div style={{ display: 'grid', gap: '1rem' }}>
          <PressureHeatmap overview={overview} onPick={pickFromHeatmap} defaultCommodity={form.commodity} />
          <div style={grid}>
            <MatchesPanel matches={matches} needsSettings={!settings || !settings.home_region} onAnalyse={analyseListing} />
            <AlertsFeed alerts={alerts} />
            <ShipmentsPanel shipments={shipments} onChange={changeShipment} busyId={busyShipment} />
          </div>
          <SettingsPanel settings={settings} regions={regions} commodities={commodities}
                         onSave={saveSettings} saving={savingSettings} />
        </div>
      </main>
    </div>
  );
}

const s = {
  page: { minHeight: '100vh', background: C.bg, fontFamily: "'Segoe UI','Outfit',sans-serif", color: C.text },
  header: {
    position: 'sticky', top: 0, zIndex: 100, background: '#fff',
    borderBottom: '1px solid #d1e7d1', boxShadow: '0 2px 12px rgba(34,118,50,0.08)',
  },
  headerInner: {
    maxWidth: 1100, margin: '0 auto', padding: '0.8rem 1rem',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.8rem', flexWrap: 'wrap',
  },
  logo: { fontFamily: 'Georgia,serif', fontSize: '1.2rem', fontWeight: 900, color: C.ink, letterSpacing: '0.06em' },
  title: { margin: 0, fontSize: 'clamp(1rem,2.2vw,1.3rem)', fontWeight: 800, color: C.ink },
  back: {
    background: '#f0fdf4', border: '1.5px solid #bbf7d0', color: '#15803d', borderRadius: 100,
    padding: '0.4rem 1rem', fontSize: '0.78rem', fontWeight: 600, cursor: 'pointer',
  },
  body: { maxWidth: 1100, margin: '0 auto', padding: '1.2rem 1rem 4rem', boxSizing: 'border-box' },
};
