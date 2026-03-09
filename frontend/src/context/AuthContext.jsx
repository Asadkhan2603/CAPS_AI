import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  apiClient,
  clearAuthStorage,
  readAuthStorage,
  REFRESH_TOKEN_KEY,
  removeAuthStorage,
  TOKEN_KEY,
  USER_KEY,
  writeAuthStorage
} from '../services/apiClient';

const AUTH_STORAGE_VERSION_KEY = 'caps_ai_auth_storage_version';
const AUTH_STORAGE_VERSION = '3';
const SESSION_STARTED_AT_KEY = 'caps_ai_session_started_at';
const LAST_ACTIVITY_AT_KEY = 'caps_ai_last_activity_at';

const DEFAULT_IDLE_TIMEOUT_MINUTES = 30;
const DEFAULT_MAX_SESSION_HOURS = 8;
const SESSION_CHECK_INTERVAL_MS = 15_000;

const AuthContext = createContext(null);

function toPositiveNumber(value, fallback) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

const IDLE_TIMEOUT_MS =
  toPositiveNumber(import.meta.env.VITE_AUTH_IDLE_TIMEOUT_MINUTES, DEFAULT_IDLE_TIMEOUT_MINUTES) * 60 * 1000;
const MAX_SESSION_MS =
  toPositiveNumber(import.meta.env.VITE_AUTH_MAX_SESSION_HOURS, DEFAULT_MAX_SESSION_HOURS) * 60 * 60 * 1000;

function readTimestamp(key) {
  const value = Number(readAuthStorage(key));
  return Number.isFinite(value) && value > 0 ? value : 0;
}

function parseStoredUser() {
  try {
    const raw = readAuthStorage(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(readAuthStorage(TOKEN_KEY) || '');
  const [user, setUser] = useState(() => parseStoredUser());
  const [checking, setChecking] = useState(Boolean(readAuthStorage(TOKEN_KEY)));

  const clearClientSession = useCallback(() => {
    clearAuthStorage();
    removeAuthStorage(SESSION_STARTED_AT_KEY);
    removeAuthStorage(LAST_ACTIVITY_AT_KEY);
    setToken('');
    setUser(null);
  }, []);

  const isSessionExpired = useCallback(() => {
    const now = Date.now();
    const sessionStartedAt = readTimestamp(SESSION_STARTED_AT_KEY);
    const lastActivityAt = readTimestamp(LAST_ACTIVITY_AT_KEY);
    if (sessionStartedAt && now - sessionStartedAt > MAX_SESSION_MS) {
      return true;
    }
    if (lastActivityAt && now - lastActivityAt > IDLE_TIMEOUT_MS) {
      return true;
    }
    return false;
  }, []);

  useEffect(() => {
    let currentVersion = '';
    try {
      currentVersion = globalThis.localStorage?.getItem(AUTH_STORAGE_VERSION_KEY) || '';
    } catch {
      currentVersion = '';
    }
    if (currentVersion !== AUTH_STORAGE_VERSION) {
      clearClientSession();
      try {
        globalThis.localStorage?.setItem(AUTH_STORAGE_VERSION_KEY, AUTH_STORAGE_VERSION);
      } catch {
        // Ignore auth storage version persistence issues.
      }
    }
  }, [clearClientSession]);

  useEffect(() => {
    async function validateToken() {
      if (!token) {
        setChecking(false);
        return;
      }
      if (isSessionExpired()) {
        clearClientSession();
        setChecking(false);
        return;
      }

      try {
        const response = await apiClient.get('/auth/me');
        const me = response.data;
        setUser(me);
        writeAuthStorage(USER_KEY, JSON.stringify(me));
      } catch {
        clearClientSession();
      } finally {
        setChecking(false);
      }
    }

    validateToken();
  }, [token, clearClientSession, isSessionExpired]);

  useEffect(() => {
    if (!token) {
      return undefined;
    }

    const now = Date.now();
    if (!readTimestamp(SESSION_STARTED_AT_KEY)) {
      writeAuthStorage(SESSION_STARTED_AT_KEY, String(now));
    }
    if (!readTimestamp(LAST_ACTIVITY_AT_KEY)) {
      writeAuthStorage(LAST_ACTIVITY_AT_KEY, String(now));
    }

    const markActivity = () => writeAuthStorage(LAST_ACTIVITY_AT_KEY, String(Date.now()));
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        markActivity();
      }
    };

    const activityEvents = ['pointerdown', 'mousemove', 'keydown', 'touchstart', 'scroll'];
    activityEvents.forEach((eventName) => {
      window.addEventListener(eventName, markActivity, { passive: true });
    });
    document.addEventListener('visibilitychange', onVisibilityChange);

    const timer = window.setInterval(() => {
      if (isSessionExpired()) {
        clearClientSession();
      }
    }, SESSION_CHECK_INTERVAL_MS);

    return () => {
      window.clearInterval(timer);
      activityEvents.forEach((eventName) => {
        window.removeEventListener(eventName, markActivity);
      });
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [token, clearClientSession, isSessionExpired]);

  const refreshUser = useCallback(async () => {
    if (!token) {
      return null;
    }
    if (isSessionExpired()) {
      clearClientSession();
      return null;
    }
    const response = await apiClient.get('/auth/me');
    const me = response.data;
    writeAuthStorage(USER_KEY, JSON.stringify(me));
    writeAuthStorage(LAST_ACTIVITY_AT_KEY, String(Date.now()));
    setUser(me);
    return me;
  }, [token, clearClientSession, isSessionExpired]);

  const login = useCallback(async (email, password) => {
    const response = await apiClient.post('/auth/login', { email, password });
    const nextToken = response.data.access_token;
    const nextRefreshToken = response.data.refresh_token || '';
    const nextUser = response.data.user;
    const now = Date.now();

    writeAuthStorage(TOKEN_KEY, nextToken);
    if (nextRefreshToken) {
      writeAuthStorage(REFRESH_TOKEN_KEY, nextRefreshToken);
    } else {
      removeAuthStorage(REFRESH_TOKEN_KEY);
    }
    writeAuthStorage(USER_KEY, JSON.stringify(nextUser));
    writeAuthStorage(SESSION_STARTED_AT_KEY, String(now));
    writeAuthStorage(LAST_ACTIVITY_AT_KEY, String(now));
    setToken(nextToken);
    setUser(nextUser);
    setChecking(false);
    return nextUser;
  }, []);

  const register = useCallback((payload) => apiClient.post('/auth/register', payload), []);

  const logout = useCallback(async () => {
    const refreshToken = readAuthStorage(REFRESH_TOKEN_KEY) || '';
    try {
      await apiClient.post('/auth/logout', refreshToken ? { refresh_token: refreshToken } : {});
    } catch {
      // Ignore logout API failures and clear local session regardless.
    }
    clearClientSession();
  }, [clearClientSession]);

  const value = useMemo(
    () => ({ token, user, checking, isAuthenticated: Boolean(token), login, register, logout, refreshUser }),
    [token, user, checking, login, register, logout, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuthContext must be used inside AuthProvider');
  }
  return context;
}
