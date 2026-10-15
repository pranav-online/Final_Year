/* Charts are SVG without accessible roles, so chart tests check Recharts'
   own class names to prove bars, bands, lines and markers were drawn. */
/* eslint-disable testing-library/no-container, testing-library/no-node-access */
import { fireEvent, render, screen } from '@testing-library/react';
import ActionCard from './ActionCard';
import BestMarketsTable from './BestMarketsTable';
import BestOptionCard from './BestOptionCard';
import FanChart, { buildFanData, MIN_TREND_POINTS } from './FanChart';
import FreshnessBadge from './FreshnessBadge';
import MarketCompareChart, { buildCompareData } from './MarketCompareChart';
import PressureHeatmap from './PressureHeatmap';
import SignalStrip from './SignalStrip';

beforeAll(() => {
  // Recharts measures the DOM; jsdom has no ResizeObserver.
  global.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
});

const weeks = (prices) => prices.map((p, i) => ({
  week_start: ['2026-09-14', '2026-09-21', '2026-09-28', '2026-10-05', '2026-10-12'][i], modal_price: p, markets: 12,
}));
const forecast = {
  confidence: 'high',
  horizons: [
    { h_weeks: 1, target_week: '2026-10-19', p10: 1900, p50: 2000, p90: 2150 },
    { h_weeks: 2, target_week: '2026-10-26', p10: 1850, p50: 1980, p90: 2200 },
  ],
};

const destination = (name, extra = {}) => ({
  destination: name, state: 'Telangana', distance_km: 136.1, expected_price_per_kg: 38,
  downside_price_per_kg: null, uses_forecast: false, price_basis: 'median of 2 markets',
  thin_sample: true, markets_in_sample: 2, transport: { cost: 3402.5, trucks: 1, truck_type: 'small' },
  net_price_per_kg: 34.6, expected_margin: 24597.5, roi: 8.23, roi_band: 'Good',
  roi_p10: null, roi_p10_band: null, break_even: { week: null, reason: 'needs forecasts' }, ...extra,
});
const markets = {
  quantity_kg: 1000, source: 'Guntur', source_price_per_kg: 10, source_price_basis: 'price given',
  settings_used: { commission_pct: 0 }, notes: [], inactive_factors: { reliability: 'x' },
  destinations: [
    destination('Khammam'),
    destination('Vijayawada', { thin_sample: false, markets_in_sample: 12, expected_price_per_kg: 18,
      net_price_per_kg: 17.01, expected_margin: 7012.5, roi: 8.1, distance_km: 39.5,
      transport: { cost: 987.5, trucks: 1, truck_type: 'small' } }),
  ],
};

describe('Price trend chart', () => {
  test('converts mandi prices to Rs/kg and starts the fan at today', () => {
    const rows = buildFanData(weeks([2000, 2100, 2050]), forecast.horizons);
    expect(rows[2]).toMatchObject({ week: '2026-09-28', price: 20.5, p50: 20.5, band: [20.5, 20.5] });
    expect(rows[4]).toEqual({ week: '2026-10-26', p50: 19.8, band: [18.5, 22] });
  });

  test('draws a price area, forecast band, median line and Today / Break-even markers', () => {
    const { container } = render(
      <FanChart history={weeks([2000, 2100, 2050, 2080])} forecast={forecast} breakEvenWeek="2026-10-26" width={640} />);
    expect(container.querySelectorAll('.recharts-area').length).toBe(2);  // price + band
    expect(container.querySelector('.recharts-line')).toBeInTheDocument();
    expect(screen.getByText('Today')).toBeInTheDocument();
    expect(screen.getByText('Break-even')).toBeInTheDocument();
    expect(screen.queryByText(/Not enough signal/)).not.toBeInTheDocument();
  });

  test('before enough weeks: this week\'s price and collection progress instead of a lone dot', () => {
    const { container } = render(<FanChart history={weeks([2400])} forecast={{ confidence: 'insufficient', reason: 'only 1 weeks of history', horizons: [] }} width={640} />);
    expect(screen.getByText('₹24.00')).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`1 of ${MIN_TREND_POINTS} collected`))).toBeInTheDocument();
    expect(screen.getByText('Not enough signal')).toBeInTheDocument();
    expect(container.querySelector('.recharts-wrapper')).not.toBeInTheDocument();
  });

  test('no forecast: no band and no phantom legend entry', () => {
    const { container } = render(<FanChart history={weeks([2000, 2100, 2050, 2080])} forecast={null} width={640} />);
    expect(container.querySelectorAll('.recharts-area').length).toBe(1);  // price only
    expect(screen.queryByText('Forecast (most likely)')).not.toBeInTheDocument();
  });
});

describe('Best place to sell', () => {
  test('headline answer with profit, kept price and a thin-sample warning', () => {
    const onDispatch = jest.fn();
    render(<BestOptionCard result={markets} commodityName="Tomato" onDispatch={onDispatch} />);
    expect(screen.getByRole('heading', { name: /Sell in Khammam — earn ₹24,598 profit/ })).toBeInTheDocument();
    expect(screen.getByText('₹34.60/kg')).toBeInTheDocument();
    expect(screen.getByRole('note')).toHaveTextContent('only 2 markets');
    fireEvent.click(screen.getByRole('button', { name: /Dispatch to Khammam/ }));
    expect(onDispatch).toHaveBeenCalledWith(markets.destinations[0]);
  });

  test('says plainly when every market loses money, and offers no dispatch', () => {
    const losing = { ...markets, destinations: [destination('Warangal', { expected_margin: -500, roi: 0.4, roi_band: 'Loss-Making' })] };
    render(<BestOptionCard result={losing} commodityName="Tomato" onDispatch={() => {}} />);
    expect(screen.getByText(/Every market loses money after freight/)).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});

describe('Compare markets chart', () => {
  test('splits each price into what you keep and freight per kg', () => {
    const [khammam, vijayawada] = buildCompareData(markets);
    expect(khammam).toMatchObject({ name: '⚠ Khammam', keep: 34.6, freight: 3.4, profitable: true });
    expect(vijayawada).toMatchObject({ name: 'Vijayawada', keep: 17.01, freight: 0.99 });
  });

  test('draws stacked bars with a "you paid" line', () => {
    const { container } = render(<MarketCompareChart result={markets} width={640} />);
    expect(container.querySelectorAll('.recharts-bar').length).toBe(3);
    expect(screen.getByText('You paid ₹10')).toBeInTheDocument();
    expect(screen.getByText(/2 of 2 do/)).toBeInTheDocument();
  });
});

test('ActionCard shows the action, a confidence label in words and the reason', () => {
  render(<ActionCard commodity="Tomato" location="Guntur" action={{
    action: 'SELL', confidence: 'low', reason: 'Market under pressure: arrivals 1.6x normal.',
    action_window: '1-2 days', urgency: 8, range_text: null,
  }} />);
  expect(screen.getByLabelText('Recommended action: SELL')).toBeInTheDocument();
  expect(screen.getByText('Low confidence')).toBeInTheDocument();
  expect(screen.getByText('Urgency 8/10')).toBeInTheDocument();
  expect(screen.getByText(/act within 1-2 days/)).toBeInTheDocument();
});

test('FreshnessBadge marks stale and fresh data in words, not colour alone', () => {
  const { rerender } = render(<FreshnessBadge freshness={{ stale: true, last_price_pull_at: null }} />);
  expect(screen.getByText(/Stale data/)).toBeInTheDocument();
  rerender(<FreshnessBadge freshness={{
    stale: false, last_price_pull_at: '2026-10-15T09:00:00+00:00', price_week: '2026-10-12', markets_reporting: 12,
  }} />);
  expect(screen.getByText(/Fresh data/)).toBeInTheDocument();
  expect(screen.getByText(/12 market\(s\) reporting/)).toBeInTheDocument();
});

test('SignalStrip shows progress towards each signal and explains every term', () => {
  render(<SignalStrip stateName="Andhra Pradesh" signal={{
    quadrant: 'insufficient_data', price: 1800, markets_reporting: 12, weeks_of_history: 1,
    momentum_4w: null, volatility_8w: null, price_vs_norm: null, arrivals_ratio: null, price_z: null,
  }} />);
  expect(screen.getByText('₹18.00/kg')).toBeInTheDocument();
  expect(screen.getByText(/Market pressure: Not enough data/)).toBeInTheDocument();
  expect(screen.getAllByText('Not yet')).toHaveLength(5);
  expect(screen.getByText('needs 9 weeks · 1/9')).toBeInTheDocument();
  expect(screen.getByLabelText(/compared with the same week in previous years/)).toBeInTheDocument();
});

test('Prices across states lists Rs/kg per state and analyses the clicked state', () => {
  const onPick = jest.fn();
  render(<PressureHeatmap onPick={onPick} defaultCommodity="tomato" overview={{ history_note: 'Only 1 week so far.', rows: [
    { commodity: 'tomato', scope_key: 'telangana', scope_name: 'Telangana', price: 2300, quadrant: 'insufficient_data' },
    { commodity: 'tomato', scope_key: 'tamil nadu', scope_name: 'Tamil Nadu', price: 3000, quadrant: 'glut' },
    { commodity: 'onion', scope_key: 'punjab', scope_name: 'Punjab', price: 4428, quadrant: 'insufficient_data' },
  ] }} />);
  const items = screen.getAllByRole('button', { name: /Analyse Tomato in/ });
  expect(items[0]).toHaveAccessibleName(/Tamil Nadu: ₹30.00 per kg, Glut/);  // highest price first
  fireEvent.click(items[1]);
  expect(onPick).toHaveBeenCalledWith('tomato', 'Telangana');
  fireEvent.click(screen.getByRole('tab', { name: /Onion/ }));
  expect(screen.getByRole('button', { name: /Analyse Onion in Punjab/ })).toBeInTheDocument();
});

test('Full breakdown table still flags thin samples and shows ROI bands as text', () => {
  render(<BestMarketsTable onDispatch={() => {}} result={markets} bare />);
  expect(screen.getByText(/thin sample \(2\)/)).toBeInTheDocument();
  expect(screen.getByText(/8.23× Good/)).toBeInTheDocument();
  expect(screen.queryByRole('heading')).not.toBeInTheDocument();
});
