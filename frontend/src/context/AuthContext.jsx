import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { apiClient, REFRESH_TOKEN_KEY, TOKEN_KEY } from '../services/apiClient';

const USER_KEY = 'caps_ai_user';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem(TOKEN_KEY) || '');
  const [user, setUser] = useState(() => {
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });
  const [checking, setChecking] = useState(Boolean(localStorage.getItem(TOKEN_KEY)));

  useEffect(() => {
    async function validateToken() {
      if (!token) {
        setChecking(false);
        return;
      }
      try {
        const response = await apiClient.get('/auth/me');
        const me = response.data;
        setUser(me);
        localStorage.setItem(USER_KEY, JSON.stringify(me));
      } catch {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        setToken('');
        setUser(null);
      } finally {
        setChecking(false);
      }
    }

    validateToken();
  }, [token]);

  async function refreshUser() {
    if (!token) {
      return null;
    }
    const response = await apiClient.get('/auth/me');
    const me = response.data;
    localStorage.setItem(USER_KEY, JSON.stringify(me));
    setUser(me);
    return me;
  }

  async function login(email, password) {
    const response = await apiClient.post('/auth/login', { email, password });
    const nextToken = response.data.access_token;
    const nextRefreshToken = response.data.refresh_token || '';
    const nextUser = response.data.user;
    localStorage.setItem(TOKEN_KEY, nextToken);
    if (nextRefreshToken) {
      localStorage.setItem(REFRESH_TOKEN_KEY, nextRefreshToken);
    }
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
    setToken(nextToken);
    setUser(nextUser);
    return nextUser;
  }

  async function register(payload) {
    return apiClient.post('/auth/register', payload);
  }

  async function logout() {
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY) || '';
    try {
      await apiClient.post('/auth/logout', refreshToken ? { refresh_token: refreshToken } : {});
    } catch {
      // Ignore logout API failures and clear local session regardless.
    }
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken('');
    setUser(null);
  }

  const value = useMemo(
    () => ({ token, user, checking, isAuthenticated: Boolean(token), login, register, logout, refreshUser }),
    [token, user, checking, refreshUser]
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
