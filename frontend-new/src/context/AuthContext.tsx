import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react';
import type { User, AuthState, LoginCredentials, RegisterData, AuthResponse } from '../types';
import { API_BASE_URL } from '../utils/theme';

interface AuthContextValue extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  loginWithGoogle: (credential: string) => Promise<void>;
  logout: () => void;
  updateUser: (user: Partial<User>) => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const TOKEN_KEY = 'meba_token';
const USER_KEY = 'meba_user';

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    isLoading: true,
    isAuthenticated: false,
  });

  // Load auth state from localStorage on mount
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    const userStr = localStorage.getItem(USER_KEY);

    if (token && userStr) {
      try {
        const user = JSON.parse(userStr) as User;
        setState({
          user,
          token,
          isLoading: false,
          isAuthenticated: true,
        });
      } catch {
        // Invalid stored data
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        setState((prev) => ({ ...prev, isLoading: false }));
      }
    } else {
      setState((prev) => ({ ...prev, isLoading: false }));
    }
  }, []);

  // Save auth state to localStorage
  const saveAuth = useCallback((token: string, user: User) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    setState({
      user,
      token,
      isLoading: false,
      isAuthenticated: true,
    });
  }, []);

  // Clear auth state
  const clearAuth = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setState({
      user: null,
      token: null,
      isLoading: false,
      isAuthenticated: false,
    });
  }, []);

  // Login with email/password
  const login = useCallback(async (credentials: LoginCredentials) => {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Giris basarisiz');
    }

    const data: AuthResponse = await response.json();
    saveAuth(data.access_token, data.user);
  }, [saveAuth]);

  // Register with email/password
  const register = useCallback(async (data: RegisterData) => {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Kayit basarisiz');
    }

    const result: AuthResponse = await response.json();
    saveAuth(result.access_token, result.user);
  }, [saveAuth]);

  // Login with Google OAuth
  const loginWithGoogle = useCallback(async (credential: string) => {
    const response = await fetch(`${API_BASE_URL}/auth/google`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ credential }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Google ile giris basarisiz');
    }

    const data: AuthResponse = await response.json();
    saveAuth(data.access_token, data.user);
  }, [saveAuth]);

  // Logout
  const logout = useCallback(() => {
    clearAuth();
  }, [clearAuth]);

  // Update user profile
  const updateUser = useCallback((updates: Partial<User>) => {
    setState((prev) => {
      if (!prev.user) return prev;
      const updatedUser = { ...prev.user, ...updates };
      localStorage.setItem(USER_KEY, JSON.stringify(updatedUser));
      return { ...prev, user: updatedUser };
    });
  }, []);

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        register,
        loginWithGoogle,
        logout,
        updateUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// Hook
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
