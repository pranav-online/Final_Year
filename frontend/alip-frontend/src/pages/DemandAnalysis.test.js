import { fireEvent, render, screen } from '@testing-library/react';
import * as api from '../services/api';
import DemandAnalysis from './DemandAnalysis';

jest.mock('react-router-dom', () => ({ useNavigate: () => jest.fn() }), { virtual: true });
jest.mock('react-hot-toast', () => ({ __esModule: true, default: { success: jest.fn(), error: jest.fn() } }));
jest.mock('../services/api');

beforeAll(() => {
  global.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
});

const ok = (data) => Promise.resolve({ data });

beforeEach(() => {
  jest.resetAllMocks();
  api.getPriceCommodities.mockReturnValue(ok({ commodities: [{ id: 'tomato', name: 'Tomato' }, { id: 'onion', name: 'Onion' }] }));
  api.getAllRegions.mockReturnValue(ok({ regions: ['Guntur', 'Hyderabad'] }));
  api.getBrokerSettings.mockReturnValue(ok({ settings: {
    home_region: null, watch_commodities: [], radius_km: 300, truck_type: null, commission_pct: 0,
  } }));
  api.getDemandOverview.mockReturnValue(ok({ rows: [], history_note: 'Only 1 week(s) of price history so far.' }));
  api.getDemandAlerts.mockReturnValue(ok({ alerts: [] }));
  api.getShipments.mockReturnValue(ok({ shipments: [] }));
  api.getPriceHistory.mockReturnValue(ok({ series: [{ week_start: '2026-10-12', modal_price: 2400 }] }));
});

const insufficientAnalysis = {
  commodity: 'tomato', commodity_name: 'Tomato', location: 'Guntur', state: 'Andhra Pradesh',
  action: { action: 'WATCH', confidence: 'insufficient', reason: 'Not enough signal yet: 1 week(s) of price history for this area.',
            action_window: '1-2 days', urgency: null, range_text: null },
  freshness: { stale: true, last_price_pull_at: '2026-10-13T09:00:00+00:00', price_week: '2026-10-12', markets_reporting: 3 },
  signal: { quadrant: 'insufficient_data', price: 2400, markets_reporting: 3, weeks_of_history: 1 },
  forecast: { confidence: 'insufficient', reason: 'only 1 weeks of history (need 26)', horizons: [] },
  best_markets: null,
  listed_supply_in_state: { listings: 0, quantity_kg: 0 },
};

async function analyse() {
  fireEvent.change(await screen.findByLabelText('2 · Where is it now?'), { target: { value: 'Guntur' } });
  fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
}

test('empty state before any analysis, with the heatmap history note', async () => {
  render(<DemandAnalysis />);
  expect(await screen.findByText(/Fill in the four boxes above/)).toBeInTheDocument();
  expect(screen.getByText('How to use this page')).toBeInTheDocument();
  expect(await screen.findByText('No mandi prices collected yet.')).toBeInTheDocument();
  expect(screen.getByLabelText('Matched farmer listings')).toHaveTextContent('Set your home region');
});

test('loading state while the analysis is in flight', async () => {
  api.getCommodityAnalysis.mockReturnValue(new Promise(() => {}));
  render(<DemandAnalysis />);
  await analyse();
  expect(screen.getByRole('button', { name: 'Analysing…' })).toBeDisabled();
  expect(screen.getByText('Loading analysis…')).toBeInTheDocument();
});

test('insufficient signal and stale data are stated plainly', async () => {
  api.getCommodityAnalysis.mockReturnValue(ok(insufficientAnalysis));
  render(<DemandAnalysis />);
  await analyse();
  expect(await screen.findByLabelText('Recommended action: WATCH')).toBeInTheDocument();
  expect(screen.getAllByText('Not enough signal').length).toBeGreaterThanOrEqual(1);
  expect(screen.getByText(/Stale data/)).toBeInTheDocument();
  expect(screen.getByText(/only 1 weeks of history \(need 26\)/)).toBeInTheDocument();
  expect(screen.getByText(/Add a/)).toHaveTextContent('to see the best place to sell');  // no quantity entered
  expect(api.getPriceHistory).toHaveBeenCalledWith('tomato', { state: 'Andhra Pradesh', weeks: 26 });
});

test('with quantity and price, the best place to sell comes first', async () => {
  api.getCommodityAnalysis.mockReturnValue(ok({
    ...insufficientAnalysis,
    best_markets: {
      quantity_kg: 1000, source: 'Guntur', source_price_per_kg: 10, source_price_basis: 'price given',
      settings_used: { commission_pct: 0 }, notes: [], inactive_factors: {}, destinations: [{
        destination: 'Vijayawada', state: 'Andhra Pradesh', distance_km: 39.5, expected_price_per_kg: 18,
        downside_price_per_kg: null, uses_forecast: false, price_basis: 'Andhra Pradesh state median',
        thin_sample: false, markets_in_sample: 12, transport: { cost: 987.5, trucks: 1, truck_type: 'small' },
        net_price_per_kg: 17.01, expected_margin: 7012.5, roi: 8.1, roi_band: 'Good',
        roi_p10: null, roi_p10_band: null, break_even: { week: null, reason: 'needs forecasts' },
      }],
    },
  }));
  render(<DemandAnalysis />);
  fireEvent.change(await screen.findByLabelText('3 · Quantity (kg)'), { target: { value: '1000' } });
  fireEvent.change(screen.getByLabelText('4 · You paid (₹/kg)'), { target: { value: '10' } });
  await analyse();
  expect(await screen.findByRole('heading', { name: /Sell in Vijayawada — earn ₹7,013 profit/ })).toBeInTheDocument();
  expect(screen.getByLabelText('Compare markets')).toBeInTheDocument();
  expect(api.getCommodityAnalysis).toHaveBeenCalledWith('tomato', 'Guntur', { qtyKg: 1000, pricePerKg: 10 });
});

test('API errors are shown, not swallowed', async () => {
  api.getCommodityAnalysis.mockRejectedValue({ response: { data: { detail: "Unknown location 'Atlantis'." } } });
  render(<DemandAnalysis />);
  await analyse();
  expect(await screen.findByRole('alert')).toHaveTextContent("Unknown location 'Atlantis'.");
});
