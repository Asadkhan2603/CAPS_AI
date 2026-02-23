import axios from 'axios';

export const TOKEN_KEY = 'caps_ai_token';
const MAX_TRACE_ENTRIES = 100;
const traceEntries = [];

function makeTraceId() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function pushTraceEntry(entry) {
  traceEntries.unshift(entry);
  if (traceEntries.length > MAX_TRACE_ENTRIES) {
    traceEntries.pop();
  }
}

export function getRecentApiTraceEntries() {
  return [...traceEntries];
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  const traceId = makeTraceId();
  const startedAt = Date.now();
  config.headers['X-Trace-Id'] = traceId;
  config.headers['X-Request-Id'] = traceId;
  config.metadata = { traceId, startedAt };
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => {
    const method = String(response.config?.method || 'GET').toUpperCase();
    const url = response.config?.url || '';
    const startedAt = response.config?.metadata?.startedAt || Date.now();
    const traceId = response.headers?.['x-trace-id'] || response.config?.metadata?.traceId || '-';
    const requestId = response.headers?.['x-request-id'] || traceId;
    const errorId = response.headers?.['x-error-id'] || response.data?.error_id || '';
    pushTraceEntry({
      at: new Date().toISOString(),
      method,
      url,
      status: response.status,
      durationMs: Date.now() - startedAt,
      traceId,
      requestId,
      errorId
    });
    return response;
  },
  (error) => {
    const response = error?.response;
    const config = error?.config || {};
    const method = String(config.method || 'GET').toUpperCase();
    const url = config.url || '';
    const startedAt = config.metadata?.startedAt || Date.now();
    const traceId = response?.headers?.['x-trace-id'] || config.metadata?.traceId || '-';
    const requestId = response?.headers?.['x-request-id'] || traceId;
    const errorId = response?.headers?.['x-error-id'] || response?.data?.error_id || '';
    pushTraceEntry({
      at: new Date().toISOString(),
      method,
      url,
      status: response?.status || 0,
      durationMs: Date.now() - startedAt,
      traceId,
      requestId,
      errorId
    });
    return Promise.reject(error);
  }
);
