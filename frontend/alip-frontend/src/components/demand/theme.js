/* Shared look for the Demand Analysis components (matches the page's light green theme).
   Every coloured signal also carries a text label, so meaning never depends on colour alone. */

export const C = {
  ink: '#14532d',
  text: '#1a2e1a',
  muted: '#6b7280',
  faint: '#9ca3af',
  line: '#e5e7eb',
  green: '#16a34a',
  greenSoft: '#dcfce7',
  bg: '#f0f4f0',
  card: '#ffffff',
};

export const card = {
  background: C.card,
  border: `1px solid ${C.line}`,
  borderRadius: 16,
  padding: '1.2rem 1.3rem',
  boxShadow: '0 2px 12px rgba(0,0,0,0.05)',
  minWidth: 0,
};

export const sectionTitle = {
  display: 'flex', alignItems: 'center', gap: '0.5rem',
  fontSize: '0.9rem', fontWeight: 800, color: C.ink, margin: '0 0 0.8rem',
};

export const chip = (bg, color) => ({
  display: 'inline-block', background: bg, color,
  borderRadius: 100, padding: '0.2rem 0.65rem',
  fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.03em', whiteSpace: 'nowrap',
});

export const button = {
  background: 'linear-gradient(135deg,#16a34a,#22c55e)', color: '#fff',
  border: 'none', borderRadius: 10, padding: '0.6rem 1.2rem',
  fontWeight: 700, fontSize: '0.85rem', cursor: 'pointer', fontFamily: 'inherit',
};

export const ghostButton = {
  background: '#f0fdf4', color: '#15803d', border: '1px solid #bbf7d0',
  borderRadius: 8, padding: '0.35rem 0.75rem', fontWeight: 700,
  fontSize: '0.75rem', cursor: 'pointer', fontFamily: 'inherit',
};

export const input = {
  width: '100%', boxSizing: 'border-box',
  background: '#f9fafb', border: '1.5px solid #d1fae5', borderRadius: 10,
  padding: '0.6rem 0.8rem', fontSize: '0.9rem', color: C.text, fontFamily: 'inherit',
};

export const label = {
  display: 'block', fontSize: '0.68rem', fontWeight: 700, letterSpacing: '0.08em',
  textTransform: 'uppercase', color: C.muted, marginBottom: '0.3rem',
};

/* Inferred demand-supply pressure quadrants (never called "demand"). */
export const QUADRANT = {
  strong_demand:     { label: 'Strong demand', short: 'Strong', bg: '#dcfce7', color: '#166534' },
  supply_shortage:   { label: 'Supply shortage', short: 'Short', bg: '#e0f2fe', color: '#075985' },
  balanced:          { label: 'Balanced', short: 'Normal', bg: '#f3f4f6', color: '#374151' },
  weak_demand:       { label: 'Weak demand', short: 'Weak', bg: '#fef3c7', color: '#92400e' },
  glut:              { label: 'Glut', short: 'Glut', bg: '#fee2e2', color: '#991b1b' },
  insufficient_data: { label: 'Not enough data', short: 'n/a', bg: '#f9fafb', color: '#9ca3af' },
};

export const ACTION = {
  SELL:  { bg: '#fee2e2', color: '#991b1b', border: '#ef4444', icon: '⬇' },
  HOLD:  { bg: '#dcfce7', color: '#166534', border: '#22c55e', icon: '⏸' },
  WATCH: { bg: '#f3f4f6', color: '#374151', border: '#9ca3af', icon: '👁' },
};

export const CONFIDENCE = {
  high:         { label: 'High confidence', bg: '#dcfce7', color: '#166534' },
  medium:       { label: 'Medium confidence', bg: '#fef9c3', color: '#854d0e' },
  low:          { label: 'Low confidence', bg: '#ffedd5', color: '#9a3412' },
  insufficient: { label: 'Not enough signal', bg: '#f3f4f6', color: '#6b7280' },
};

export const ROI_BAND = {
  'Good':        { bg: '#dcfce7', color: '#166534' },
  'Acceptable':  { bg: '#fef9c3', color: '#854d0e' },
  'Loss-Making': { bg: '#fee2e2', color: '#991b1b' },
};

export const rupees = (v, digits = 0) =>
  v === null || v === undefined || Number.isNaN(v)
    ? '—'
    : `₹${Number(v).toLocaleString('en-IN', { maximumFractionDigits: digits, minimumFractionDigits: digits })}`;

export const pct = (v) =>
  v === null || v === undefined ? '—' : `${v > 0 ? '+' : ''}${(v * 100).toFixed(1)}%`;

export const titleCase = (s) => (s || '').replace(/\b\w/g, (m) => m.toUpperCase());

/* Mandis report Rs per quintal (100 kg); brokers think in Rs per kg. */
export const perKg = (perQuintal, digits = 2) =>
  perQuintal === null || perQuintal === undefined ? '—' : `${rupees(perQuintal / 100, digits)}/kg`;

export const COMMODITY_ICON = {
  tomato: '🍅', banana: '🍌', onion: '🧅', potato: '🥔', maize: '🌽',
  paddy: '🌾', rice: '🍚', wheat: '🌾', cotton: '☁️', groundnut: '🥜',
};

/* Small "i" with a plain-language explanation (title tooltip + screen-reader text). */
export const infoDot = {
  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
  width: 15, height: 15, borderRadius: '50%', background: '#e5e7eb', color: '#4b5563',
  fontSize: '0.62rem', fontWeight: 800, cursor: 'help', marginLeft: 4, verticalAlign: 'middle',
};
