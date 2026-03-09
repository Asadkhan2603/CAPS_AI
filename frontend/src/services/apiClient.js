import axios from 'axios';

export const TOKEN_KEY = 'caps_ai_token';
export const REFRESH_TOKEN_KEY = 'caps_ai_refresh_token';
export const USER_KEY = 'caps_ai_user';
const MAX_TRACE_ENTRIES = 100;
const traceEntries = [];

function getSessionStore() {
  try {
    return globalThis.sessionStorage || null;
  } catch {
    return null;
  }
}

function removeLegacyLocalValue(key) {
  try {
    globalThis.localStorage?.removeItem(key);
  } catch {
    // Ignore legacy storage cleanup failures.
  }
}

export function readAuthStorage(key) {
  const store = getSessionStore();
  return store?.getItem(key) || '';
}

export function writeAuthStorage(key, value) {
  const store = getSessionStore();
  if (store) {
    store.setItem(key, value);
  }
  removeLegacyLocalValue(key);
}

export function removeAuthStorage(key) {
  const store = getSessionStore();
  store?.removeItem(key);
  removeLegacyLocalValue(key);
}

export function clearAuthStorage() {
  removeAuthStorage(TOKEN_KEY);
  removeAuthStorage(REFRESH_TOKEN_KEY);
  removeAuthStorage(USER_KEY);
}

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

function isEnvelope(payload) {
  return (
    payload &&
    typeof payload === 'object' &&
    Object.prototype.hasOwnProperty.call(payload, 'success') &&
    Object.prototype.hasOwnProperty.call(payload, 'data') &&
    Object.prototype.hasOwnProperty.call(payload, 'error')
  );
}

export function getRecentApiTraceEntries() {
  return [...traceEntries];
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1'
});

apiClient.interceptors.request.use((config) => {
  const token = readAuthStorage(TOKEN_KEY);
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
    if (isEnvelope(response.data)) {
      response.data = response.data.data;
    }
    return response;
  },
  async (error) => {
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
    if (response && isEnvelope(response?.data)) {
      const envelope = response.data;
      error.response.data = {
        ...error.response.data,
        detail: envelope?.error?.detail ?? envelope?.error?.message ?? 'Request failed',
        error_id: envelope?.error?.error_id || errorId
      };
    }

    const originalRequest = error?.config;
    const statusCode = response?.status;
    const isAuthPath =
      typeof originalRequest?.url === 'string' &&
      (originalRequest.url.includes('/auth/login') ||
        originalRequest.url.includes('/auth/refresh') ||
        originalRequest.url.includes('/auth/logout'));

    if (statusCode === 401 && originalRequest && !originalRequest._retry && !isAuthPath) {
      originalRequest._retry = true;
      const refreshToken = readAuthStorage(REFRESH_TOKEN_KEY);
      if (refreshToken) {
        try {
          const refreshResponse = await axios.post(
            `${apiClient.defaults.baseURL}/auth/refresh`,
            { refresh_token: refreshToken }
          );
          const refreshPayload = isEnvelope(refreshResponse?.data) ? refreshResponse.data.data : refreshResponse?.data;
          const nextAccessToken = refreshPayload?.access_token;
          const nextRefreshToken = refreshPayload?.refresh_token;
          if (nextAccessToken) {
            writeAuthStorage(TOKEN_KEY, nextAccessToken);
            originalRequest.headers = originalRequest.headers || {};
            originalRequest.headers.Authorization = `Bearer ${nextAccessToken}`;
          }
          if (nextRefreshToken) {
            writeAuthStorage(REFRESH_TOKEN_KEY, nextRefreshToken);
          }
          return apiClient(originalRequest);
        } catch {
          clearAuthStorage();
        }
      }
    }
    return Promise.reject(error);
  }
);
