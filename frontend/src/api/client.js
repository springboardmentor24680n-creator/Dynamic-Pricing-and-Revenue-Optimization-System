import axios from 'axios';

// In development, Vite proxies /api to the backend.
// In production, set VITE_API_URL to your backend URL.
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

let isRefreshing = false;
let refreshSubscribers = [];

function onRefreshed(token) {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

function subscribeTokenRefresh(cb) {
  refreshSubscribers.push(cb);
}

// Request interceptor to add JWT token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: on 401, try to refresh the token once, then retry the request
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Only attempt refresh for real 401s from API calls (not the refresh call itself)
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/refresh') &&
      !originalRequest.url?.includes('/auth/login') &&
      !originalRequest.url?.includes('/auth/google')
    ) {
      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        if (!window.location.pathname.startsWith('/login')) {
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }

      originalRequest._retry = true;

      if (isRefreshing) {
        // Queue this request and retry once the token is refreshed
        return new Promise((resolve, reject) => {
          subscribeTokenRefresh((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(apiClient(originalRequest));
          });
          // Safety: if refresh fails, reject
          setTimeout(() => reject(error), 15000);
        });
      }

      isRefreshing = true;
      try {
        const res = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        });
        const { access_token, refresh_token: newRefresh } = res.data;
        localStorage.setItem('access_token', access_token);
        if (newRefresh) localStorage.setItem('refresh_token', newRefresh);
        onRefreshed(access_token);
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        onRefreshed(null);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        if (!window.location.pathname.startsWith('/login')) {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;

// ======== Auth API ========
export const authAPI = {
  login: (credentials) => apiClient.post('/api/v1/auth/login', credentials),
  register: (userData) => apiClient.post('/api/v1/auth/register', userData),
  getMe: () => apiClient.get('/api/v1/auth/me'),
  updateMe: (data) => apiClient.put('/api/v1/auth/me', data),
  changePassword: (data) => apiClient.post('/api/v1/auth/change-password', data),
  refresh: (refreshToken) => apiClient.post('/api/v1/auth/refresh', { refresh_token: refreshToken }),
  google: (idToken) => apiClient.post('/api/v1/auth/google', { id_token: idToken }),
  forgotPassword: (email) => apiClient.post('/api/v1/auth/forgot-password', { email }),
  resetPassword: (token, newPassword) => apiClient.post('/api/v1/auth/reset-password', { token, new_password: newPassword }),
};

// ======== Dashboard API ========
export const dashboardAPI = {
  getDashboard: () => apiClient.get('/api/v1/dashboard/'),
};

// ======== Products API ========
export const productsAPI = {
  list: (params) => apiClient.get('/api/v1/products/', { params }),
  getById: (id) => apiClient.get(`/api/v1/products/${id}`),
  create: (data) => apiClient.post('/api/v1/products/', data),
  update: (id, data) => apiClient.put(`/api/v1/products/${id}`, data),
  delete: (id) => apiClient.delete(`/api/v1/products/${id}`),
  toggleStatus: (id, status) => apiClient.patch(`/api/v1/products/${id}/status`, { status }),
  bulkDelete: (ids) => apiClient.post('/api/v1/products/bulk-delete', { ids }),
  bulkStatus: (ids, status) => apiClient.post('/api/v1/products/bulk-status', { ids, status }),
  getCategories: () => apiClient.get('/api/v1/products/categories/all'),
  exportCsv: (params) => apiClient.get('/api/v1/products/export/csv', { params, responseType: 'blob' }),
};

// ======== Pricing API ========
export const pricingAPI = {
  updatePrice: (productId, data) => apiClient.put(`/api/v1/pricing/products/${productId}/price`, data),
  getHistory: (productId, params) => apiClient.get(`/api/v1/pricing/products/${productId}/history`, { params }),
  listRecommendations: (params) => apiClient.get('/api/v1/pricing/recommendations', { params }),
  approveRecommendation: (id) => apiClient.post(`/api/v1/pricing/recommendations/${id}/approve`),
  rejectRecommendation: (id) => apiClient.post(`/api/v1/pricing/recommendations/${id}/reject`),
};

// ======== AI API ========
export const aiAPI = {
  getStatus: () => apiClient.get('/api/v1/ai/status'),
  modelInfo: () => apiClient.get('/api/v1/ai/model-info'),
  train: () => apiClient.post('/api/v1/ai/train'),
  retrain: () => apiClient.post('/api/v1/ai/retrain'),
  predict: (productId, params) => apiClient.get(`/api/v1/ai/predict/${productId}`, { params }),
  optimize: (productId, params) => apiClient.get(`/api/v1/ai/optimize/${productId}`, { params }),
  saveRecommendation: (productId) => apiClient.post(`/api/v1/ai/optimize/${productId}/save`, {}),
  batchOptimize: (params) => apiClient.get('/api/v1/ai/batch-optimize', { params }),
  predictRevenue: (productId, newPrice) => apiClient.post(`/api/v1/ai/predict-revenue/${productId}?new_price=${newPrice}`),
  forecast: (productId, horizon = 30, force = false) =>
    apiClient.get(`/api/v1/ai/forecast/${productId}`, { params: { horizon, force } }),
  forecastPortfolio: (horizon = 30) =>
    apiClient.get('/api/v1/ai/forecast', { params: { horizon } }),
  report: (productId, horizon = 30) =>
    apiClient.get(`/api/v1/ai/report/${productId}`, { params: { horizon } }),
  exportReport: (productId, format, horizon = 30) =>
    apiClient.get(`/api/v1/ai/report/${productId}/export`, {
      params: { format, horizon },
      responseType: 'blob',
    }),
};

// ======== Datasets API ========
export const datasetsAPI = {
  list: (params) => apiClient.get('/api/v1/datasets/', { params }),
  getStats: () => apiClient.get('/api/v1/datasets/stats'),
  getTypes: () => apiClient.get('/api/v1/datasets/types'),
  upload: (file, datasetType = 'custom') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('dataset_type', datasetType);
    return apiClient.post('/api/v1/datasets/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  importDataset: (id) => apiClient.post(`/api/v1/datasets/${id}/import`),
  preview: (id) => apiClient.get(`/api/v1/datasets/${id}/preview`),
};

// ======== Users API ========
export const usersAPI = {
  list: () => apiClient.get('/api/v1/users/'),
  create: (data) => apiClient.post('/api/v1/users/', data),
  update: (userId, data) => apiClient.put(`/api/v1/users/${userId}`, data),
  toggleStatus: (userId) => apiClient.put(`/api/v1/users/${userId}/status`),
  resetPassword: (userId, newPassword) => apiClient.post(`/api/v1/users/${userId}/reset-password`, { new_password: newPassword }),
  delete: (userId) => apiClient.delete(`/api/v1/users/${userId}`),
};

// ======== Activity API ========
export const activityAPI = {
  getLogs: (params) => apiClient.get('/api/v1/activity/logs', { params }),
};

// ======== Access Requests API (admin approval workflow) ========
export const accessRequestsAPI = {
  list: (params) => apiClient.get('/api/v1/access-requests/', { params }),
  pendingCount: () => apiClient.get('/api/v1/access-requests/pending-count'),
  approve: (requestId, role) => apiClient.post(`/api/v1/access-requests/${requestId}/approve`, { role }),
  reject: (requestId) => apiClient.post(`/api/v1/access-requests/${requestId}/reject`),
};

// ======== Reports API ========
export const reportsAPI = {
  revenue: () => apiClient.get('/api/v1/reports/revenue'),
  pricing: () => apiClient.get('/api/v1/reports/pricing-performance'),
  products: () => apiClient.get('/api/v1/reports/product-performance'),
  users: () => apiClient.get('/api/v1/reports/users'),
  datasets: () => apiClient.get('/api/v1/reports/datasets'),
  export: (reportType, format) =>
    apiClient.get(`/api/v1/reports/export?report_type=${reportType}&format=${format}`, {
      responseType: 'blob',
    }),
};

// ======== Sales API ========
export const salesAPI = {
  analytics: (days) => apiClient.get('/api/v1/sales/analytics', { params: { days } }),
};

// ======== Competitor Monitoring API ========
export const competitorAPI = {
  analyze: (productId) => apiClient.get(`/api/v1/competitors/${productId}`),
  platforms: () => apiClient.get('/api/v1/competitors/platforms/list'),
};

// ======== Market Intelligence API ========
export const marketAPI = {
  analyze: (productId) => apiClient.get(`/api/v1/market-intelligence/${productId}`),
  report: (productId, horizon = 30) =>
    apiClient.get(`/api/v1/market-intelligence/${productId}/report`, { params: { horizon } }),
};

// ======== Profitability Analytics API ========
export const profitabilityAPI = {
  summary: (days) => apiClient.get('/api/v1/profitability/summary', { params: { days } }),
  trends: (days) => apiClient.get('/api/v1/profitability/trends', { params: { days } }),
  products: (params) => apiClient.get('/api/v1/profitability/products', { params }),
  categories: (days) => apiClient.get('/api/v1/profitability/categories', { params: { days } }),
  aiImpact: (days, topN) => apiClient.get('/api/v1/profitability/ai-impact', { params: { days, top_n: topN } }),
  opportunities: (days) => apiClient.get('/api/v1/profitability/opportunities', { params: { days } }),
};

// ======== Business Intelligence API ========
export const biAPI = {
  summary: (days) => apiClient.get('/api/v1/business-intelligence/summary', { params: { days } }),
  refresh: (days) => apiClient.post('/api/v1/business-intelligence/refresh', null, { params: { days } }),
  cacheStatus: () => apiClient.get('/api/v1/business-intelligence/cache-status'),
};

// ======== Pricing Strategy API ========
export const pricingStrategyAPI = {
  recommendations: (params) => apiClient.get('/api/v1/pricing-strategy/recommendations', { params }),
  productRecommendation: (productId) => apiClient.get(`/api/v1/pricing-strategy/recommendations/${productId}`),
  summary: (params) => apiClient.get('/api/v1/pricing-strategy/summary', { params }),
  categories: () => apiClient.get('/api/v1/pricing-strategy/categories'),
};

// ======== Loaders API (legacy) ========
export const loadersAPI = {
  loadRetailPricing: () => apiClient.post('/loaders/retail-pricing'),
  uploadRetailPricing: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post('/loaders/retail-pricing/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  loadEcommerceSales: () => apiClient.post('/loaders/ecommerce-sales'),
  uploadEcommerceSales: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post('/loaders/ecommerce-sales/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// ======== Download helper ========
export function downloadBlob(response, fallbackName = 'download') {
  const disposition = response.headers?.['content-disposition'] || '';
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match ? match[1] : fallbackName;
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
