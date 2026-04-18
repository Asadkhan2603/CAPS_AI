import axios from 'axios';
import FingerprintJS from '@fingerprintjs/fingerprintjs-pro';

export const TOKEN_KEY = 'caps_ai_token';
export const REFRESH_TOKEN_KEY = 'caps_ai_refresh_token';
export const USER_KEY = 'caps_ai_user';
export const DEVICE_FINGERPRINT_KEY = 'caps_ai_device_fingerprint';
let accessToken = '';
let deviceFingerprint = '';
const MAX_TRACE_ENTRIES = 100;
const traceEntries = [];
const TRAILING_SLASH_COLLECTION_PATHS = new Set([
  '/assignments',
  '/attendance-records',
  '/audit-logs',
  '/batches',
  '/class-slots',
  '/clubs',
  '/course-offerings',
  '/departments',
  '/enrollments',
  '/evaluations',
  '/event-registrations',
  '/exams',
  '/faculties',
  '/groups',
  '/notifications',
  '/programs',
  '/review-tickets',
  '/sections',
  '/semesters',
  '/specializations',
  '/students',
  '/subjects',
  '/submissions',
  '/timetables',
  '/universities',
  '/users'
]);

function logApiDiagnostic(message, error) {
  if (import.meta.env.DEV) {
    console.warn(message, error);
  }
}

function readFromStore(storeName, key) {
  try {
    return globalThis?.[storeName]?.getItem(key) || '';
  } catch {
    return '';
  }
}

function writeToStore(storeName, key, value) {
  try {
    globalThis?.[storeName]?.setItem(key, value);
  } catch {
    // Ignore storage persistence failures.
  }
}

function removeFromStore(storeName, key) {
  try {
    globalThis?.[storeName]?.removeItem(key);
  } catch {
    // Ignore storage cleanup failures.
  }
}

export function readAuthStorage(key) {
  return readFromStore('sessionStorage', key) || readFromStore('localStorage', key) || '';
}

export function writeAuthStorage(key, value) {
  writeToStore('sessionStorage', key, value);
  writeToStore('localStorage', key, value);
}

export function removeAuthStorage(key) {
  removeFromStore('sessionStorage', key);
  removeFromStore('localStorage', key);
}

export function clearAuthStorage() {
  accessToken = '';
  removeAuthStorage(TOKEN_KEY);
  removeAuthStorage(REFRESH_TOKEN_KEY);
  removeAuthStorage(USER_KEY);
}

export function setAccessToken(token) {
  accessToken = String(token || '');
  removeAuthStorage(TOKEN_KEY);
}

export function getAccessToken() {
  return accessToken;
}

async function getDeviceFingerprint() {
  if (deviceFingerprint) {
    return deviceFingerprint;
  }

  const fingerprintApiKey = import.meta.env.VITE_FINGERPRINT_API_KEY || '';
  if (!fingerprintApiKey) {
    const cached = readFromStore('sessionStorage', DEVICE_FINGERPRINT_KEY) || readFromStore('localStorage', DEVICE_FINGERPRINT_KEY);
    if (cached) {
      deviceFingerprint = cached;
      return deviceFingerprint;
    }
    return '';
  }

  try {
    const fp = await FingerprintJS.load({ apiKey: fingerprintApiKey });
    const result = await fp.get();
    deviceFingerprint = result.visitorId;
    writeToStore('sessionStorage', DEVICE_FINGERPRINT_KEY, deviceFingerprint);
    return deviceFingerprint;
  } catch (error) {
    logApiDiagnostic('Failed to generate device fingerprint:', error);
    const cached = readFromStore('sessionStorage', DEVICE_FINGERPRINT_KEY) || readFromStore('localStorage', DEVICE_FINGERPRINT_KEY);
    if (cached) {
      deviceFingerprint = cached;
      return deviceFingerprint;
    }
    return '';
  }
}

function setDeviceFingerprint(fp) {
  deviceFingerprint = fp;
  if (fp) {
    writeToStore('sessionStorage', DEVICE_FINGERPRINT_KEY, fp);
  }
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

function normalizeCollectionRootUrl(url) {
  if (typeof url !== 'string' || !url.startsWith('/')) {
    return url;
  }

  const [path, query = ''] = url.split('?');
  if (!TRAILING_SLASH_COLLECTION_PATHS.has(path)) {
    return url;
  }

  return query ? `${path}/?${query}` : `${path}/`;
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

export function isRefreshExemptAuthPath(url) {
  if (typeof url !== 'string') {
    return false;
  }

  return (
    url.includes('/auth/login') ||
    url.includes('/auth/refresh') ||
    url.includes('/auth/logout') ||
    url.includes('/auth/mfa/')
  );
}

export function getRecentApiTraceEntries() {
  return [...traceEntries];
}

export function terminateSession(sessionId) {
  return apiClient.post(`/auth/sessions/${sessionId}/terminate`);
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1'
});

apiClient.interceptors.request.use(async (config) => {
  config.url = normalizeCollectionRootUrl(config.url);
  const token = accessToken || readAuthStorage(TOKEN_KEY);
  const traceId = makeTraceId();
  const startedAt = Date.now();
  config.headers['X-Trace-Id'] = traceId;
  config.headers['X-Request-Id'] = traceId;
  config.metadata = { traceId, startedAt };
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  
  // Add device fingerprint header for anomaly detection
  try {
    const fingerprint = await getDeviceFingerprint();
    if (fingerprint) {
      config.headers['X-Device-Fingerprint'] = fingerprint;
    }
  } catch (error) {
    logApiDiagnostic('Failed to add device fingerprint header:', error);
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
    const isAuthPath = isRefreshExemptAuthPath(originalRequest?.url);

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
            setAccessToken(nextAccessToken);
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
