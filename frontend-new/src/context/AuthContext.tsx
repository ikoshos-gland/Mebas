/**
 * Authentication Context - Firebase Authentication
 *
 * Manages user authentication state using Firebase Auth.
 * Syncs with backend for user profile data.
 */
import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react';
import {
  type User as FirebaseUser,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  signOut,
  onAuthStateChanged,
  sendPasswordResetEmail,
  updateProfile,
} from 'firebase/auth';
import { auth, googleProvider } from '../config/firebase';
import type { User } from '../types';
import { API_BASE_URL } from '../utils/theme';

interface AuthState {
  user: User | null;
  firebaseUser: FirebaseUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  logout: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  getIdToken: () => Promise<string | null>;
  completeProfile: (data: { role: string; grade?: number; full_name?: string }) => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [firebaseUser, setFirebaseUser] = useState<FirebaseUser | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  /**
   * Get current Firebase ID token
   */
  const getIdToken = useCallback(async (): Promise<string | null> => {
    if (!firebaseUser) return null;
    try {
      return await firebaseUser.getIdToken();
    } catch {
      return null;
    }
  }, [firebaseUser]);

  /**
   * Fetch user profile from backend
   */
  const fetchUserProfile = useCallback(async (fbUser: FirebaseUser): Promise<User | null> => {
    try {
      const idToken = await fbUser.getIdToken();
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: {
          Authorization: `Bearer ${idToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        return await response.json();
      }

      // If 401, token might be invalid
      if (response.status === 401) {
        console.warn('Backend rejected token, signing out');
        await signOut(auth);
        return null;
      }

      console.error('Failed to fetch user profile:', response.status);
      return null;
    } catch (error) {
      console.error('Error fetching user profile:', error);
      return null;
    }
  }, []);

  /**
   * Refresh user data from backend
   */
  const refreshUser = useCallback(async () => {
    if (!firebaseUser) return;
    const userData = await fetchUserProfile(firebaseUser);
    if (userData) {
      setUser(userData);
    }
  }, [firebaseUser, fetchUserProfile]);

  /**
   * Listen to Firebase auth state changes
   */
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (fbUser) => {
      setFirebaseUser(fbUser);

      if (fbUser) {
        const userData = await fetchUserProfile(fbUser);
        setUser(userData);
      } else {
        setUser(null);
      }

      setIsLoading(false);
    });

    return () => unsubscribe();
  }, [fetchUserProfile]);

  /**
   * Login with email/password
   */
  const login = useCallback(async (email: string, password: string) => {
    const result = await signInWithEmailAndPassword(auth, email, password);
    const userData = await fetchUserProfile(result.user);
    setUser(userData);
  }, [fetchUserProfile]);

  /**
   * Register with email/password
   */
  const register = useCallback(
    async (email: string, password: string, displayName: string) => {
      const result = await createUserWithEmailAndPassword(auth, email, password);

      // Update display name in Firebase
      await updateProfile(result.user, { displayName });

      // Fetch user profile (will be auto-created by backend)
      const userData = await fetchUserProfile(result.user);
      setUser(userData);
    },
    [fetchUserProfile]
  );

  /**
   * Login with Google
   */
  const loginWithGoogle = useCallback(async () => {
    const result = await signInWithPopup(auth, googleProvider);
    const userData = await fetchUserProfile(result.user);
    setUser(userData);
  }, [fetchUserProfile]);

  /**
   * Logout
   */
  const logout = useCallback(async () => {
    await signOut(auth);
    setUser(null);
  }, []);

  /**
   * Reset password
   */
  const resetPassword = useCallback(async (email: string) => {
    await sendPasswordResetEmail(auth, email);
  }, []);

  /**
   * Complete profile (for first-time users)
   */
  const completeProfile = useCallback(
    async (data: { role: string; grade?: number; full_name?: string }) => {
      if (!firebaseUser) throw new Error('Oturum acilmamis');

      const idToken = await firebaseUser.getIdToken();
      const response = await fetch(`${API_BASE_URL}/auth/complete-profile`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${idToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Profil tamamlanamadi');
      }

      const userData = await response.json();
      setUser(userData);
    },
    [firebaseUser]
  );

  return (
    <AuthContext.Provider
      value={{
        user,
        firebaseUser,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        loginWithGoogle,
        logout,
        resetPassword,
        getIdToken,
        completeProfile,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
