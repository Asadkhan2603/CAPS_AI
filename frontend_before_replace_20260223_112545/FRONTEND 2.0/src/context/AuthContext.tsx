import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiClient } from '../services/apiClient';

interface User {
  id: string;
  full_name: string;
  email: string;
  role: 'admin' | 'teacher' | 'student';
  extended_roles?: string[];
  avatar_url?: string | null;
  avatar_updated_at?: string | null;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const savedToken = localStorage.getItem('caps_ai_token');
      const savedUser = localStorage.getItem('caps_ai_user');

      if (savedToken && savedUser) {
        setToken(savedToken);
        setUser(JSON.parse(savedUser));
        
        try {
          // Validate session
          const response = await apiClient.get('/auth/me');
          setUser(response.data);
          localStorage.setItem('caps_ai_user', JSON.stringify(response.data));
        } catch (error) {
          console.error('Session validation failed', error);
          logout();
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = (newToken: string, newUser: User) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem('caps_ai_token', newToken);
    localStorage.setItem('caps_ai_user', JSON.stringify(newUser));
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('caps_ai_token');
    localStorage.removeItem('caps_ai_user');
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
