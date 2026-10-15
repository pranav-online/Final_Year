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

// ─── Market APIs ───────────────────────────────────────────
export const addCropListing = (data) =>
  api.post('/market/listing/add', data);

export const getMarketListings = () =>
  api.get('/market/listings');

export const getRegionalSupply = (region) =>
  api.get(`/market/supply/${encodeURIComponent(region)}`);

export const getAllRegionalSupply = () =>
  api.get('/market/supply');

export const getDemandAnalysis = (region, crop = null) =>
  api.get(`/market/demand/${encodeURIComponent(region.trim())}`, {
    params: crop ? { crop } : {},
  });

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

export const getRegionalDemandEstimate = (region, crop) =>
  api.get(
    `/market/demand/threshold/${encodeURIComponent(region)}/${encodeURIComponent(crop)}`
  );

export default api;
export const getNotifications = () =>
  api.get('/notifications/alerts');