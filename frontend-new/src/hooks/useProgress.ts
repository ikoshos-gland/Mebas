/**
 * useProgress Hook - Kazanim progress tracking
 *
 * Fetches and manages user's learning progress from the backend.
 */
import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../utils/theme';
import type {
  KazanimProgress,
  ProgressStats,
  PrerequisiteRecommendation,
  ProgressListResponse,
} from '../types';

interface UseProgressReturn {
  progress: KazanimProgress[];
  stats: ProgressStats | null;
  recommendations: PrerequisiteRecommendation[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
  // Counts for quick access
  understoodCount: number;
  trackedCount: number;
  inProgressCount: number;
}

export const useProgress = (): UseProgressReturn => {
  const { getIdToken, isAuthenticated } = useAuth();
  const [progress, setProgress] = useState<KazanimProgress[]>([]);
  const [stats, setStats] = useState<ProgressStats | null>(null);
  const [recommendations, setRecommendations] = useState<PrerequisiteRecommendation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Counts derived from progress
  const understoodCount = progress.filter((p) => p.status === 'understood').length;
  const trackedCount = progress.filter((p) => p.status === 'tracked').length;
  const inProgressCount = progress.filter((p) => p.status === 'in_progress').length;

  const fetchProgress = useCallback(async () => {
    if (!isAuthenticated) {
      setProgress([]);
      setIsLoading(false);
      return;
    }

    const token = await getIdToken();
    if (!token) {
      setProgress([]);
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/users/me/progress`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Progress yuklenemedi');
      }

      const data: ProgressListResponse = await response.json();
      setProgress(data.items);
      setError(null);
    } catch (err) {
      console.error('Progress fetch error:', err);
      setError(err instanceof Error ? err.message : 'Progress yuklenemedi');
      setProgress([]);
    }
  }, [getIdToken, isAuthenticated]);

  const fetchStats = useCallback(async () => {
    if (!isAuthenticated) {
      setStats(null);
      return;
    }

    const token = await getIdToken();
    if (!token) {
      setStats(null);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/users/me/progress/stats`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data: ProgressStats = await response.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Stats fetch error:', err);
      // Don't set error for stats - it's not critical
    }
  }, [getIdToken, isAuthenticated]);

  const fetchRecommendations = useCallback(async () => {
    if (!isAuthenticated) {
      setRecommendations([]);
      return;
    }

    const token = await getIdToken();
    if (!token) {
      setRecommendations([]);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/users/me/progress/recommendations?limit=5`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data: PrerequisiteRecommendation[] = await response.json();
        setRecommendations(data);
      }
    } catch (err) {
      console.error('Recommendations fetch error:', err);
      // Don't set error for recommendations - it's not critical
    }
  }, [getIdToken, isAuthenticated]);

  const refetch = useCallback(() => {
    setIsLoading(true);
    Promise.all([fetchProgress(), fetchStats(), fetchRecommendations()]).finally(() => {
      setIsLoading(false);
    });
  }, [fetchProgress, fetchStats, fetchRecommendations]);

  // Initial fetch
  useEffect(() => {
    if (isAuthenticated) {
      refetch();
    } else {
      setIsLoading(false);
    }
  }, [isAuthenticated]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    progress,
    stats,
    recommendations,
    isLoading,
    error,
    refetch,
    understoodCount,
    trackedCount,
    inProgressCount,
  };
};

export default useProgress;
