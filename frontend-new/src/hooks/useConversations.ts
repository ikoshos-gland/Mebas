/**
 * useConversations Hook - Conversation management
 *
 * Fetches and manages user's conversations from the backend.
 */
import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../utils/theme';
import type {
  Conversation,
  ConversationListResponse,
  ConversationWithMessages,
} from '../types';

interface UseConversationsReturn {
  conversations: Conversation[];
  isLoading: boolean;
  error: string | null;
  hasMore: boolean;
  total: number;
  refetch: () => void;
  loadMore: () => void;
  createConversation: (title?: string, subject?: string, grade?: number) => Promise<Conversation | null>;
  deleteConversation: (id: string) => Promise<boolean>;
  getConversation: (id: string) => Promise<ConversationWithMessages | null>;
}

export const useConversations = (): UseConversationsReturn => {
  const { getIdToken, isAuthenticated } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [total, setTotal] = useState(0);

  const fetchConversations = useCallback(async (pageNum: number = 1, append: boolean = false) => {
    if (!isAuthenticated) {
      setConversations([]);
      setIsLoading(false);
      return;
    }

    const token = await getIdToken();
    if (!token) {
      setConversations([]);
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/conversations?page=${pageNum}&page_size=20`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Sohbetler yuklenemedi');
      }

      const data: ConversationListResponse = await response.json();

      if (append) {
        setConversations((prev) => [...prev, ...data.items]);
      } else {
        setConversations(data.items);
      }
      setHasMore(data.has_more);
      setTotal(data.total);
      setError(null);
    } catch (err) {
      console.error('Conversations fetch error:', err);
      setError(err instanceof Error ? err.message : 'Sohbetler yuklenemedi');
      if (!append) {
        setConversations([]);
      }
    }
  }, [getIdToken, isAuthenticated]);

  const refetch = useCallback(() => {
    setIsLoading(true);
    setPage(1);
    fetchConversations(1, false).finally(() => {
      setIsLoading(false);
    });
  }, [fetchConversations]);

  const loadMore = useCallback(() => {
    if (hasMore && !isLoading) {
      const nextPage = page + 1;
      setPage(nextPage);
      fetchConversations(nextPage, true);
    }
  }, [hasMore, isLoading, page, fetchConversations]);

  const createConversation = useCallback(async (
    title?: string,
    subject?: string,
    grade?: number
  ): Promise<Conversation | null> => {
    if (!isAuthenticated) return null;

    const token = await getIdToken();
    if (!token) return null;

    try {
      const response = await fetch(`${API_BASE_URL}/conversations`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: title || 'Yeni Sohbet',
          subject,
          grade,
        }),
      });

      if (!response.ok) {
        throw new Error('Sohbet olusturulamadi');
      }

      const conversation: Conversation = await response.json();
      setConversations((prev) => [conversation, ...prev]);
      setTotal((prev) => prev + 1);
      return conversation;
    } catch (err) {
      console.error('Create conversation error:', err);
      return null;
    }
  }, [getIdToken, isAuthenticated]);

  const deleteConversation = useCallback(async (id: string): Promise<boolean> => {
    if (!isAuthenticated) return false;

    const token = await getIdToken();
    if (!token) return false;

    try {
      const response = await fetch(`${API_BASE_URL}/conversations/${id}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Sohbet silinemedi');
      }

      setConversations((prev) => prev.filter((c) => c.id !== id));
      setTotal((prev) => prev - 1);
      return true;
    } catch (err) {
      console.error('Delete conversation error:', err);
      return false;
    }
  }, [getIdToken, isAuthenticated]);

  const getConversation = useCallback(async (id: string): Promise<ConversationWithMessages | null> => {
    if (!isAuthenticated) return null;

    const token = await getIdToken();
    if (!token) return null;

    try {
      const response = await fetch(`${API_BASE_URL}/conversations/${id}`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          return null;
        }
        throw new Error('Sohbet yuklenemedi');
      }

      const conversation: ConversationWithMessages = await response.json();
      return conversation;
    } catch (err) {
      console.error('Get conversation error:', err);
      return null;
    }
  }, [getIdToken, isAuthenticated]);

  // Initial fetch
  useEffect(() => {
    if (isAuthenticated) {
      refetch();
    } else {
      setIsLoading(false);
    }
  }, [isAuthenticated]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    conversations,
    isLoading,
    error,
    hasMore,
    total,
    refetch,
    loadMore,
    createConversation,
    deleteConversation,
    getConversation,
  };
};

export default useConversations;
