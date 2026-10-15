import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add token to every request automatically
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// The backend now validates the token on protected routes. If it is missing
// or expired (401), clear the stale session and send the user to log in again.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const url = error.config?.url || '';
    if (status === 401 && !url.startsWith('/auth/')) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      if (window.location.pathname !== '/login') {
        window.location.assign('/login');
      }
    }
    return Promise.reject(error);
  }
);

// ─── Auth APIs ─────────────────────────────────────────────
export const registerUser = (data) =>
  api.post('/auth/register', data);

export const loginUser = (data) =>
  api.post('/auth/login', data);

// ─── Disease APIs ──────────────────────────────────────────
export const predictDisease = (formData) =>
  api.post('/disease/predict', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });

export const getDiseaseStatus = () =>
  api.get('/disease/status');

// ─── Weather APIs ──────────────────────────────────────────
export const getWeatherAdvisory = (location, disease = null, severity = null) => {
  const params = {};
  if (disease) params.disease = disease;
  if (severity) params.severity = severity;
  return api.get(`/weather/advisory/${encodeURIComponent(location)}`, { params });
};

// ─── Crop APIs ─────────────────────────────────────────────
export const getCropRecommendation = (data) =>
  api.post('/crop/recommend', data);

export const getSoilProfile = (latitude, longitude) =>
  api.get('/crop/soil-profile', { params: { latitude, longitude } });

export const reverseGeocode = (latitude, longitude) =>
  api.get('/crop/reverse-geocode', { params: { latitude, longitude } });

// ─── Market APIs ───────────────────────────────────────────
export const addCropListing = (data) =>
  api.post('/market/listing/add', data);

export const getMarketListings = () =>
  api.get('/market/listings');

export const getRegionalSupply = (region) =>
  api.get(`/market/supply/${encodeURIComponent(region)}`);

export const getAllRegionalSupply = () =>
  api.get('/market/supply');

export const getMarketSummary = () =>
  api.get('/market/summary');

// ─── Region and Location APIs ─────────────────────────────
export const getAllRegions = () =>
  api.get('/market/regions/all');

export const getRegionInfo = (region) =>
  api.get(`/market/regions/info/${encodeURIComponent(region)}`);

export const getNearestRegions = (region, crop, maxKm = 500) =>
  api.get(
    `/market/regions/nearest/${encodeURIComponent(region)}/${encodeURIComponent(crop)}`,
    { params: { max_km: maxKm } }
  );

export const getRegionDistance = (region1, region2) =>
  api.get(
    `/market/regions/distance/${encodeURIComponent(region1)}/${encodeURIComponent(region2)}`
  );

// ─── Demand Analysis (mandi data, signals, forecasts, decisions) ──
export const getPriceCommodities = () =>
  api.get('/market/prices/commodities');

export const getPriceHistory = (commodity, { state, marketKey, weeks = 26 } = {}) =>
  api.get('/market/prices/history', {
    params: { commodity, state: state || undefined, market_key: marketKey || undefined, weeks },
  });

export const getDemandOverview = (level = 'state', { state, commodities } = {}) =>
  api.get('/market/demand/overview', {
    params: { level, state: state || undefined, commodities: commodities || undefined },
  });

export const getCommodityAnalysis = (commodity, location, { qtyKg, pricePerKg } = {}) =>
  api.get(`/market/demand/analysis/${encodeURIComponent(commodity)}`, {
    params: { location, qty_kg: qtyKg || undefined, price_per_kg: pricePerKg || undefined },
  });

export const getDemandAlerts = (limit = 20) =>
  api.get('/market/demand/alerts', { params: { limit } });

export const getBrokerSettings = () =>
  api.get('/market/demand/settings');

export const saveBrokerSettings = (settings) =>
  api.put('/market/demand/settings', settings);

export const getListingMatches = (commodity = null) =>
  api.get('/market/demand/matches', { params: commodity ? { commodity } : {} });

export const initiateShipment = (data) =>
  api.post('/market/demand/initiate-shipment', data);

export const getShipments = () =>
  api.get('/market/demand/shipments');

export const updateShipmentStatus = (id, status) =>
  api.post(`/market/demand/shipments/${encodeURIComponent(id)}/status`, { status });

export const getDataHealth = () =>
  api.get('/health/data');

export default api;
export const getNotifications = () =>
  api.get('/notifications/alerts');