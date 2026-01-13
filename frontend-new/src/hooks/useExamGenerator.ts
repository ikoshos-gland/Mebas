/**
 * useExamGenerator Hook - Exam generation and management
 *
 * Handles exam PDF generation based on user's tracked kazanimlar.
 */
import { useState, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../utils/theme';
import type {
  ExamGenerateRequest,
  ExamGenerateResponse,
  ExamListItem,
  ExamListResponse,
  AvailableQuestionsStats,
} from '../types';

interface UseExamGeneratorReturn {
  // State
  isGenerating: boolean;
  isLoading: boolean;
  error: string | null;
  lastGeneratedExam: ExamGenerateResponse | null;
  exams: ExamListItem[];
  availableStats: AvailableQuestionsStats | null;

  // Actions
  generateExam: (options?: ExamGenerateRequest) => Promise<ExamGenerateResponse | null>;
  fetchExams: () => Promise<void>;
  fetchAvailableStats: () => Promise<void>;
  deleteExam: (examId: string) => Promise<boolean>;
  downloadExam: (examId: string) => void;
  clearError: () => void;
}

export const useExamGenerator = (): UseExamGeneratorReturn => {
  const { getIdToken, isAuthenticated } = useAuth();

  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastGeneratedExam, setLastGeneratedExam] = useState<ExamGenerateResponse | null>(null);
  const [exams, setExams] = useState<ExamListItem[]>([]);
  const [availableStats, setAvailableStats] = useState<AvailableQuestionsStats | null>(null);

  const clearError = useCallback(() => setError(null), []);

  /**
   * Generate a new exam PDF
   */
  const generateExam = useCallback(
    async (options?: ExamGenerateRequest): Promise<ExamGenerateResponse | null> => {
      if (!isAuthenticated) {
        setError('Sinav olusturmak icin giris yapmaniz gerekiyor.');
        return null;
      }

      const token = await getIdToken();
      if (!token) {
        setError('Oturum gecersiz. Lutfen tekrar giris yapin.');
        return null;
      }

      setIsGenerating(true);
      setError(null);

      try {
        const response = await fetch(`${API_BASE_URL}/exams/generate`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            title: options?.title || 'Calisma Sinavi',
            question_count: options?.question_count || 10,
            difficulty_distribution: options?.difficulty_distribution || {
              kolay: 0.3,
              orta: 0.5,
              zor: 0.2,
            },
            kazanim_codes: options?.kazanim_codes || null,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || 'Sinav olusturulamadi');
        }

        const data: ExamGenerateResponse = await response.json();
        setLastGeneratedExam(data);
        return data;
      } catch (err) {
        console.error('Exam generation error:', err);
        setError(err instanceof Error ? err.message : 'Sinav olusturulamadi');
        return null;
      } finally {
        setIsGenerating(false);
      }
    },
    [getIdToken, isAuthenticated]
  );

  /**
   * Fetch user's exam list
   */
  const fetchExams = useCallback(async () => {
    if (!isAuthenticated) {
      setExams([]);
      return;
    }

    const token = await getIdToken();
    if (!token) {
      setExams([]);
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/exams/`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Sinavlar yuklenemedi');
      }

      const data: ExamListResponse = await response.json();
      setExams(data.exams);
    } catch (err) {
      console.error('Exam list fetch error:', err);
      setError(err instanceof Error ? err.message : 'Sinavlar yuklenemedi');
      setExams([]);
    } finally {
      setIsLoading(false);
    }
  }, [getIdToken, isAuthenticated]);

  /**
   * Fetch available questions statistics
   */
  const fetchAvailableStats = useCallback(async () => {
    if (!isAuthenticated) {
      setAvailableStats(null);
      return;
    }

    const token = await getIdToken();
    if (!token) {
      setAvailableStats(null);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/exams/stats/available`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Istatistikler yuklenemedi');
      }

      const data: AvailableQuestionsStats = await response.json();
      setAvailableStats(data);
    } catch (err) {
      console.error('Available stats fetch error:', err);
      // Don't set error - this is not critical
    }
  }, [getIdToken, isAuthenticated]);

  /**
   * Delete an exam
   */
  const deleteExam = useCallback(
    async (examId: string): Promise<boolean> => {
      if (!isAuthenticated) {
        setError('Sinav silmek icin giris yapmaniz gerekiyor.');
        return false;
      }

      const token = await getIdToken();
      if (!token) {
        setError('Oturum gecersiz.');
        return false;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/exams/${examId}`, {
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          throw new Error('Sinav silinemedi');
        }

        // Update local state
        setExams((prev) => prev.filter((exam) => exam.exam_id !== examId));
        return true;
      } catch (err) {
        console.error('Exam delete error:', err);
        setError(err instanceof Error ? err.message : 'Sinav silinemedi');
        return false;
      }
    },
    [getIdToken, isAuthenticated]
  );

  /**
   * Download exam PDF
   */
  const downloadExam = useCallback(
    async (examId: string) => {
      if (!isAuthenticated) {
        setError('Indirmek icin giris yapmaniz gerekiyor.');
        return;
      }

      const token = await getIdToken();
      if (!token) {
        setError('Oturum gecersiz.');
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/exams/${examId}/download`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          throw new Error('PDF indirilemedi');
        }

        // Create blob and download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `sinav_${examId}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } catch (err) {
        console.error('Exam download error:', err);
        setError(err instanceof Error ? err.message : 'PDF indirilemedi');
      }
    },
    [getIdToken, isAuthenticated]
  );

  return {
    isGenerating,
    isLoading,
    error,
    lastGeneratedExam,
    exams,
    availableStats,
    generateExam,
    fetchExams,
    fetchAvailableStats,
    deleteExam,
    downloadExam,
    clearError,
  };
};

export default useExamGenerator;
