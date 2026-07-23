import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import axios from 'axios';

const API = process.env.REACT_APP_API_URL;

interface User {
  id: string;
  name: string;
  email: string;
  is_admin: boolean;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Set up axios interceptor once at module level
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses globally
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.log('Got 401, clearing auth');
      localStorage.removeItem('token');
      localStorage.removeItem('user');
    }
    return Promise.reject(error);
  }
);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const savedToken = localStorage.getItem('token');
    const savedUser = localStorage.getItem('user');
    
    if (savedToken && savedUser) {
      try {
        const parsedUser = JSON.parse(savedUser);
        setToken(savedToken);
        setUser(parsedUser);
        console.log('Loaded user from storage:', parsedUser);
      } catch (e) {
        console.error('Failed to parse saved user:', e);
        localStorage.removeItem('token');
        localStorage.removeItem('user');
      }
    }
    
    setLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    const res = await axios.post(`${API}/auth/login`, { email, password }, { timeout: 120000 });
    const { token: newToken, user: newUser } = res.data;
    
    localStorage.setItem('token', newToken);
    localStorage.setItem('user', JSON.stringify(newUser));
    
    setToken(newToken);
    setUser(newUser);
    
    console.log('Logged in:', newUser);
  };

  const register = async (name: string, email: string, password: string) => {
    const res = await axios.post(`${API}/auth/register`, { name, email, password }, { timeout: 120000 });
    const { token: newToken, user: newUser } = res.data;
    
    localStorage.setItem('token', newToken);
    localStorage.setItem('user', JSON.stringify(newUser));
    
    setToken(newToken);
    setUser(newUser);
    
    console.log('Registered:', newUser);
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}