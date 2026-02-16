import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { apiClient, TOKEN_KEY } from '../services/apiClient';

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
        localStorage.removeItem(USER_KEY);
        setToken('');
        setUser(null);
      } finally {
        setChecking(false);
      }
    }

    validateToken();
  }, [token]);

  async function login(email, password) {
    const response = await apiClient.post('/auth/login', { email, password });
    const nextToken = response.data.access_token;
    const nextUser = response.data.user;
    localStorage.setItem(TOKEN_KEY, nextToken);
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
    setToken(nextToken);
    setUser(nextUser);
    return nextUser;
  }

  async function register(payload) {
    return apiClient.post('/auth/register', payload);
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken('');
    setUser(null);
  }

  const value = useMemo(
    () => ({ token, user, checking, isAuthenticated: Boolean(token), login, register, logout }),
    [token, user, checking]
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
