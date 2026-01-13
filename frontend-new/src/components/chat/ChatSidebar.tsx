/**
 * ChatSidebar - Conversation history sidebar
 *
 * Shows list of past conversations with ability to:
 * - Create new conversation
 * - Switch between conversations
 * - Delete conversations
 */
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Plus,
  MessageSquare,
  Trash2,
  Search,
  X,
  ChevronLeft,
  Loader2,
  Clock,
} from 'lucide-react';
import { useConversations } from '../../hooks/useConversations';
import type { Conversation } from '../../types';

interface ChatSidebarProps {
  currentConversationId?: string;
  isOpen: boolean;
  onClose: () => void;
}

// Format relative time in Turkish
const formatRelativeTime = (dateString: string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return 'Az once';
  if (diffMins < 60) return `${diffMins}dk`;
  if (diffHours < 24) return `${diffHours}sa`;
  if (diffDays === 1) return 'Dun';
  if (diffDays < 7) return `${diffDays}g`;
  return date.toLocaleDateString('tr-TR', { day: 'numeric', month: 'short' });
};

export const ChatSidebar = ({
  currentConversationId,
  isOpen,
  onClose,
}: ChatSidebarProps) => {
  const navigate = useNavigate();
  const {
    conversations,
    isLoading,
    deleteConversation,
  } = useConversations();

  const [searchQuery, setSearchQuery] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Filter conversations by search query
  const filteredConversations = conversations.filter((conv) =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Group conversations by date
  const groupedConversations = filteredConversations.reduce(
    (groups, conv) => {
      const date = new Date(conv.updated_at || conv.created_at);
      const today = new Date();
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);

      let groupKey: string;
      if (date.toDateString() === today.toDateString()) {
        groupKey = 'Bugun';
      } else if (date.toDateString() === yesterday.toDateString()) {
        groupKey = 'Dun';
      } else if (date > new Date(today.setDate(today.getDate() - 7))) {
        groupKey = 'Bu Hafta';
      } else {
        groupKey = 'Daha Eski';
      }

      if (!groups[groupKey]) {
        groups[groupKey] = [];
      }
      groups[groupKey].push(conv);
      return groups;
    },
    {} as Record<string, Conversation[]>
  );

  const handleNewChat = () => {
    navigate('/sohbet');
    onClose();
  };

  const handleSelectConversation = (id: string) => {
    navigate(`/sohbet/${id}`);
    onClose();
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (deletingId) return;

    setDeletingId(id);
    const success = await deleteConversation(id);
    setDeletingId(null);

    if (success && currentConversationId === id) {
      navigate('/sohbet');
    }
  };

  return (
    <>
      {/* Backdrop for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:relative inset-y-0 left-0 z-50
          w-72 bg-paper border-r border-stone-200
          flex flex-col
          transform transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          lg:translate-x-0
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-stone-200">
          <h2 className="font-serif-custom text-lg italic text-sepia">
            Sohbetler
          </h2>
          <button
            onClick={onClose}
            className="lg:hidden p-2 hover:bg-stone-100 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-5 h-5 text-neutral-500" />
          </button>
        </div>

        {/* New Chat Button */}
        <div className="p-3">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-ink text-paper rounded-xl hover:bg-sepia transition-colors font-sans text-sm font-medium shadow-md"
          >
            <Plus className="w-4 h-4" />
            Yeni Sohbet
          </button>
        </div>

        {/* Search */}
        <div className="px-3 pb-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
            <input
              type="text"
              placeholder="Sohbet ara..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-stone-50 border border-stone-200 rounded-lg text-sm focus:outline-none focus:border-sepia focus:ring-1 focus:ring-sepia/20 transition-colors"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto px-3 pb-3">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 text-sepia animate-spin" />
            </div>
          ) : filteredConversations.length === 0 ? (
            <div className="text-center py-8">
              <MessageSquare className="w-10 h-10 text-neutral-300 mx-auto mb-3" />
              <p className="text-sm text-neutral-500">
                {searchQuery ? 'Sonuc bulunamadi' : 'Henuz sohbet yok'}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {Object.entries(groupedConversations).map(([group, convs]) => (
                <div key={group}>
                  <h3 className="font-mono-custom text-[10px] uppercase tracking-wider text-neutral-400 px-2 mb-2">
                    {group}
                  </h3>
                  <div className="space-y-1">
                    {convs.map((conv) => (
                      <button
                        key={conv.id}
                        onClick={() => handleSelectConversation(conv.id)}
                        className={`
                          w-full text-left px-3 py-2.5 rounded-lg transition-all group
                          ${
                            currentConversationId === conv.id
                              ? 'bg-sepia/10 border border-sepia/20'
                              : 'hover:bg-stone-50 border border-transparent'
                          }
                        `}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <p
                              className={`text-sm font-sans truncate ${
                                currentConversationId === conv.id
                                  ? 'text-sepia font-medium'
                                  : 'text-ink'
                              }`}
                            >
                              {conv.title}
                            </p>
                            <div className="flex items-center gap-2 mt-1">
                              {conv.subject && (
                                <span className="font-mono-custom text-[10px] text-sepia/70">
                                  {conv.subject}
                                </span>
                              )}
                              <span className="flex items-center gap-1 font-mono-custom text-[10px] text-neutral-400">
                                <Clock className="w-3 h-3" />
                                {formatRelativeTime(conv.updated_at || conv.created_at)}
                              </span>
                            </div>
                          </div>

                          {/* Delete button */}
                          <button
                            onClick={(e) => handleDelete(e, conv.id)}
                            disabled={deletingId === conv.id}
                            className={`
                              p-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity
                              ${
                                deletingId === conv.id
                                  ? 'text-neutral-400'
                                  : 'text-neutral-400 hover:text-red-500 hover:bg-red-50'
                              }
                            `}
                          >
                            {deletingId === conv.id ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Trash2 className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-stone-200">
          <Link
            to="/panel"
            className="flex items-center justify-center gap-2 text-sm text-neutral-500 hover:text-sepia transition-colors"
          >
            Tum istatistikler icin Panel'e git
          </Link>
        </div>
      </aside>
    </>
  );
};

export default ChatSidebar;
