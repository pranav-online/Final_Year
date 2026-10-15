import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { addCropListing } from '../services/api';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';
import './CropListing.css';

/* ── UI helpers (display only) ─────────────────────────────── */
const CROP_EMOJIS = [
  ['rice', '🌾'], ['paddy', '🌾'], ['wheat', '🌾'], ['maize', '🌽'], ['corn', '🌽'],
  ['cotton', '☁️'], ['sugarcane', '🎋'], ['tomato', '🍅'], ['potato', '🥔'], ['onion', '🧅'],
  ['banana', '🍌'], ['mango', '🥭'], ['chilli', '🌶️'], ['chili', '🌶️'], ['groundnut', '🥜'],
  ['coconut', '🥥'], ['apple', '🍎'], ['grape', '🍇'], ['orange', '🍊'], ['lemon', '🍋'],
  ['coffee', '☕'], ['tea', '🍵'], ['pulse', '🫘'], ['dal', '🫘'], ['gram', '🫘'], ['bean', '🫘'],
];
const getEmoji = (name) => {
  const n = String(name || '').toLowerCase();
  const hit = CROP_EMOJIS.find(([k]) => n.includes(k));
  return hit ? hit[1] : '🌱';
};

// Smoothly animates a number toward its target
function useAnimatedNumber(target, ms = 600) {
  const [val, setVal] = useState(0);
  const fromRef = useRef(0);
  useEffect(() => {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { setVal(target); fromRef.current = target; return; }
    const from = fromRef.current;
    let raf, start;
    const tick = (t) => {
      start = start ?? t;
      const p = Math.min((t - start) / ms, 1);
      const v = from + (target - from) * (1 - Math.pow(1 - p, 3));
      setVal(v);
      fromRef.current = v;
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, ms]);
  return val;
}

const inr = (n) => Math.round(n).toLocaleString('en-IN');

const FIELDS = [
  { key: 'farmer_name',  label: 'Farmer Name *',    type: 'text',   placeholder: 'Your name',        icon: '👨‍🌾', wide: true },
  { key: 'location',     label: 'Location *',       type: 'text',   placeholder: 'City/District',    icon: '📍' },
  { key: 'crop_name',    label: 'Crop Name *',      type: 'text',   placeholder: 'e.g. rice, wheat', icon: '🌾' },
  { key: 'quantity_kg',  label: 'Quantity (kg) *',  type: 'number', placeholder: 'e.g. 500',         icon: '⚖️' },
  { key: 'price_per_kg', label: 'Price per kg (₹)*', type: 'number', placeholder: 'e.g. 25',         icon: '₹' },
  { key: 'contact',      label: 'Contact Number',   type: 'text',   placeholder: 'Phone number',     icon: '📞', wide: true },
];

export default function CropListing() {
  const navigate    = useNavigate();
  const { user }    = useAuth();
  const [form, setForm] = useState({
    farmer_name:   user?.full_name || '',
    location:      '',
    crop_name:     '',
    quantity_kg:   '',
    price_per_kg:  '',
    status:        'available',
    contact:       ''
  });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const quantity = Number(form.quantity_kg);
    const price = Number(form.price_per_kg);
    if (!form.farmer_name.trim() || !form.location.trim() || !form.crop_name.trim()) {
      toast.error('Enter your name, location, and crop.');
      return;
    }
    if (!Number.isFinite(quantity) || quantity <= 0 || !Number.isFinite(price) || price <= 0) {
      toast.error('Quantity and price must be greater than zero.');
      return;
    }
    setLoading(true);
    try {
      await addCropListing({
        ...form,
        farmer_name: form.farmer_name.trim(),
        location: form.location.trim(),
        crop_name: form.crop_name.trim(),
        quantity_kg: quantity,
        price_per_kg: price
      });
      toast.success('Crop listing added successfully!');
      setSuccess(true);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add listing. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  /* preview values (display only) */
  const qty = Number(form.quantity_kg);
  const price = Number(form.price_per_kg);
  const hasQty = Number.isFinite(qty) && qty > 0;
  const hasPrice = Number.isFinite(price) && price > 0;
  const total = useAnimatedNumber(hasQty && hasPrice ? qty * price : 0);
  const emoji = getEmoji(form.crop_name);

  const required = ['farmer_name', 'location', 'crop_name', 'quantity_kg', 'price_per_kg'];
  const filled = required.filter((k) => String(form[k]).trim() !== '').length;
  const pct = Math.round((filled / required.length) * 100);

  const goBack = () => navigate(user?.role === 'broker' ? '/broker' : '/farmer');

  if (success) {
    return (
      <div className="cl-root">
        <div className="cl-success">
          {Array.from({ length: 16 }).map((_, i) => (
            <span
              key={i}
              className="cl-confetti"
              style={{ left: `${(i * 37) % 100}%`, animationDelay: `${(i % 8) * 0.35}s`, animationDuration: `${4 + (i % 5)}s` }}
              aria-hidden="true"
            >
              {['🌱', '🌾', '🍃'][i % 3]}
            </span>
          ))}
          <div className="cl-success-box">
            <svg className="cl-check" viewBox="0 0 100 100" aria-hidden="true">
              <circle className="cl-check-circle" cx="50" cy="50" r="46" />
              <path className="cl-check-tick" d="M30 52 L45 66 L71 36" />
            </svg>
            <h2 className="cl-success-title">Listing Added!</h2>
            <p className="cl-success-text">
              Your crop has been listed in the market successfully.
            </p>
            <div className="cl-success-actions">
              <button
                className="cl-btn cl-btn-primary"
                onClick={() => {
                  setSuccess(false);
                  setForm({...form, crop_name: '', quantity_kg: '', price_per_kg: ''});
                }}
              >
                ➕ Add Another
              </button>
              <button
                className="cl-btn cl-btn-secondary"
                onClick={goBack}
              >
                ← Go Back
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="cl-root">
      <header className="cl-header">
        <div className="cl-header-inner">
          <button className="cl-back" onClick={goBack}>
            ← Back
          </button>
          <div className="cl-title-wrap">
            <div className="cl-logo">📦</div>
            <div>
              <h1 className="cl-title">Add Crop Listing</h1>
              <p className="cl-sub">List your harvest for brokers to find</p>
            </div>
          </div>
        </div>
      </header>

      <main className="cl-main">
        {/* ── Form ── */}
        <form className="cl-card" onSubmit={handleSubmit}>
          <h2 className="cl-card-title">List Your Crop for Sale</h2>
          <p className="cl-card-desc">
            Fill in the details to list your crop in the market
          </p>

          <div className="cl-progress">
            <div className="cl-progress-top">
              <span>Listing details</span>
              <b>{filled} of {required.length} required filled</b>
            </div>
            <div className="cl-progress-track">
              <div className="cl-progress-bar" style={{ width: `${pct}%` }} />
            </div>
          </div>

          <div className="cl-grid">
            {FIELDS.map((field, i) => (
              <div
                key={field.key}
                className={`cl-field${field.wide ? ' is-wide' : ''}`}
                style={{ animationDelay: `${0.1 + i * 0.06}s` }}
              >
                <label className="cl-label">{field.label}</label>
                <div className="cl-input-wrap">
                  <span className="cl-input-icon">{field.icon}</span>
                  <input
                    className={`cl-input${String(form[field.key]).trim() !== '' ? ' is-filled' : ''}`}
                    type={field.type}
                    required={field.key !== 'contact'}
                    min={field.type === 'number' ? '0.01' : undefined}
                    step={field.type === 'number' ? 'any' : undefined}
                    placeholder={field.placeholder}
                    value={form[field.key]}
                    onChange={(e) => setForm({...form, [field.key]: e.target.value})}
                  />
                </div>
              </div>
            ))}
          </div>

          <button
            className="cl-submit"
            onClick={handleSubmit}
            disabled={loading}
          >
            <span className="cl-submit-inner">
              {loading ? (<><span className="cl-spinner" /> Adding...</>) : '📦 Add Listing'}
            </span>
          </button>
        </form>

        {/* ── Live preview ticket ── */}
        <aside className="cl-side" aria-label="Listing preview">
          <p className="cl-side-label"><span className="cl-live-dot" /> Live preview</p>
          <div className="cl-ticket">
            <div className="cl-ticket-top">
              <div className="cl-ticket-row">
                <span className="cl-emoji" key={emoji}>{emoji}</span>
                <div>
                  <h3 className={`cl-ticket-crop${form.crop_name.trim() ? '' : ' is-empty'}`}>
                    {form.crop_name.trim() || 'Your crop'}
                  </h3>
                  <p className="cl-ticket-loc">📍 {form.location.trim() || 'Location'}</p>
                </div>
              </div>
              <span className="cl-status"><i /> Available</span>
            </div>

            <div className="cl-perf"><span /></div>

            <div className="cl-ticket-body">
              <div className="cl-stats">
                <div className="cl-stat">
                  <span>Quantity</span>
                  <strong className={hasQty ? '' : 'is-empty'}>{hasQty ? `${qty.toLocaleString('en-IN')} kg` : '— kg'}</strong>
                </div>
                <div className="cl-stat">
                  <span>Price</span>
                  <strong className={hasPrice ? '' : 'is-empty'}>{hasPrice ? `₹${price.toLocaleString('en-IN')}/kg` : '₹ —/kg'}</strong>
                </div>
              </div>

              <div className="cl-total">
                <span>Total value</span>
                <strong className={hasQty && hasPrice ? '' : 'is-empty'}>
                  {hasQty && hasPrice ? `₹${inr(total)}` : '₹ 0'}
                </strong>
              </div>

              <div className="cl-meta">
                <div className={form.farmer_name.trim() ? '' : 'is-empty'}>👨‍🌾 {form.farmer_name.trim() || 'Farmer name'}</div>
                <div className={form.contact.trim() ? '' : 'is-empty'}>📞 {form.contact.trim() || 'Contact number (optional)'}</div>
              </div>
            </div>
          </div>
          <p className="cl-hint">This is how brokers will see your listing. Total value is quantity × price per kg.</p>
        </aside>
      </main>
    </div>
  );
}