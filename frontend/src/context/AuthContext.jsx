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
import { fetchSessionBootstrap } from './sessionBootstrap';

const AUTH_STORAGE_VERSION_KEY = 'caps_ai_auth_storage_version';
const AUTH_STORAGE_VERSION = '3';
const SESSION_STARTED_AT_KEY = 'caps_ai_session_started_at';
const LAST_ACTIVITY_AT_KEY = 'caps_ai_last_activity_at';
const SESSION_BOOTSTRAP_KEY = 'caps_ai_session_bootstrap';

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

function parseStoredBootstrap() {
  try {
    const raw = readAuthStorage(SESSION_BOOTSTRAP_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(readAuthStorage(TOKEN_KEY) || '');
  const [user, setUser] = useState(() => parseStoredUser());
  const [sessionBootstrap, setSessionBootstrap] = useState(() => parseStoredBootstrap());
  const [checking, setChecking] = useState(Boolean(readAuthStorage(TOKEN_KEY)));
  const [loginAnomaly, setLoginAnomaly] = useState(null);

  const clearClientSession = useCallback(() => {
    clearAuthStorage();
    removeAuthStorage(SESSION_STARTED_AT_KEY);
    removeAuthStorage(LAST_ACTIVITY_AT_KEY);
    removeAuthStorage(SESSION_BOOTSTRAP_KEY);
    setToken('');
    setUser(null);
    setSessionBootstrap(null);
  }, []);

  const applySessionBootstrap = useCallback((payload) => {
    if (!payload || !payload.user) {
      return null;
    }
    writeAuthStorage(USER_KEY, JSON.stringify(payload.user));
    writeAuthStorage(SESSION_BOOTSTRAP_KEY, JSON.stringify(payload));
    setUser(payload.user);
    setSessionBootstrap(payload);
    return payload.user;
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
        const payload = await fetchSessionBootstrap(apiClient);
        applySessionBootstrap(payload);
      } catch {
        clearClientSession();
      } finally {
        setChecking(false);
      }
    }

    validateToken();
  }, [token, applySessionBootstrap, clearClientSession, isSessionExpired]);

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
    const payload = await fetchSessionBootstrap(apiClient);
    const me = applySessionBootstrap(payload);
    writeAuthStorage(LAST_ACTIVITY_AT_KEY, String(Date.now()));
    return me;
  }, [token, applySessionBootstrap, clearClientSession, isSessionExpired]);

  const persistAuthenticatedSession = useCallback(async (loginPayload) => {
    const nextToken = loginPayload?.access_token || '';
    const nextRefreshToken = loginPayload?.refresh_token || '';
    const nextUser = loginPayload?.user || null;
    const anomaly = loginPayload?.anomaly || null;
    const now = Date.now();

    if (!nextToken || !nextUser) {
      throw new Error('Authenticated session payload is incomplete');
    }

    if (anomaly?.new_device || anomaly?.new_network) {
      setLoginAnomaly(anomaly);
    } else {
      setLoginAnomaly(null);
    }

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

    try {
      const payload = await fetchSessionBootstrap(apiClient);
      const bootstrapUser = applySessionBootstrap(payload);
      setChecking(false);
      return bootstrapUser || nextUser;
    } catch {
      const fallbackBootstrap = {
        user: nextUser,
        unread_notice_count: 0,
        unread_notification_count: 0,
        branding: { has_logo: false, updated_at: null, filename: null },
        generated_at: new Date().toISOString()
      };
      applySessionBootstrap(fallbackBootstrap);
      setChecking(false);
      return nextUser;
    }
  }, [applySessionBootstrap]);

  const login = useCallback(async (email, password) => {
    const response = await apiClient.post('/auth/login', { email, password });
    const payload = response?.data || {};

    if (payload?.mfa_required) {
      return {
        mfaRequired: true,
        pendingMfaToken: payload.pending_mfa_token,
        mfaMethods: payload.mfa_methods || [],
        primaryMethod: payload.mfa_primary_method || null,
        challenge: payload.mfa_challenge || null,
        user: payload.user || null
      };
    }

    const user = await persistAuthenticatedSession(payload);
    return {
      mfaRequired: false,
      user
    };
  }, [persistAuthenticatedSession]);

  const completeMfaLogin = useCallback(async ({ pendingMfaToken, method, code }) => {
    const response = await apiClient.post('/auth/mfa/verify', {
      pending_mfa_token: pendingMfaToken,
      mfa_method: method,
      mfa_code: code
    });
    const user = await persistAuthenticatedSession(response.data);
    return { user };
  }, [persistAuthenticatedSession]);

  const beginWebAuthnMfaLogin = useCallback(async (pendingMfaToken) => {
    const response = await apiClient.post('/auth/mfa/webauthn/authenticate/begin', {
      pending_mfa_token: pendingMfaToken
    });
    return response.data;
  }, []);

  const completeWebAuthnMfaLogin = useCallback(async ({ pendingMfaToken, credential }) => {
    const response = await apiClient.post('/auth/mfa/webauthn/authenticate/finish', {
      pending_mfa_token: pendingMfaToken,
      credential
    });
    const user = await persistAuthenticatedSession(response.data);
    return { user };
  }, [persistAuthenticatedSession]);

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
    () => ({
      token,
      user,
      sessionBootstrap,
      checking,
      loginAnomaly,
      isAuthenticated: Boolean(token),
      login,
      completeMfaLogin,
      beginWebAuthnMfaLogin,
      completeWebAuthnMfaLogin,
      register,
      logout,
      refreshUser,
      refreshBootstrap: refreshUser
    }),
    [
      token,
      user,
      sessionBootstrap,
      checking,
      loginAnomaly,
      login,
      completeMfaLogin,
      beginWebAuthnMfaLogin,
      completeWebAuthnMfaLogin,
      register,
      logout,
      refreshUser
    ]
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
