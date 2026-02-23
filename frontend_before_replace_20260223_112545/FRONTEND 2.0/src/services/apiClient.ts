import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('caps_ai_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  // Add Trace Headers
  const traceId = crypto.randomUUID();
  const requestId = crypto.randomUUID();
  config.headers['X-Trace-Id'] = traceId;
  config.headers['X-Request-Id'] = requestId;

  return config;
});

// Response Interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle global errors (e.g. 401 Unauthorized)
    if (error.response?.status === 401) {
      localStorage.removeItem('caps_ai_token');
      localStorage.removeItem('caps_ai_user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);
