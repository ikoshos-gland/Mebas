/**
 * KazanimCard - Individual kazanim progress card
 *
 * Displays a single kazanim with its status (tracked, in_progress, understood)
 * Includes clickable status icon with confirmation dialog
 */
import { useState } from 'react';
import { CheckCircle, Circle, Clock, ChevronRight, Loader2, X } from 'lucide-react';
import { Card, Button } from '../common';
import { useAuth } from '../../context/AuthContext';
import { API_BASE_URL } from '../../utils/theme';
import type { KazanimProgress, KazanimProgressStatus } from '../../types';

interface KazanimCardProps {
  progress: KazanimProgress;
  onSelect?: (code: string) => void;
  onStatusChange?: () => void;
}

const statusConfig: Record<
  KazanimProgressStatus,
  { icon: typeof CheckCircle; color: string; bgColor: string; hoverBg: string; label: string }
> = {
  tracked: {
    icon: Circle,
    color: 'text-neutral-400',
    bgColor: 'bg-stone-100',
    hoverBg: 'hover:bg-green-100 hover:text-green-500',
    label: 'Takipte',
  },
  in_progress: {
    icon: Clock,
    color: 'text-amber-500',
    bgColor: 'bg-amber-100',
    hoverBg: 'hover:bg-green-100 hover:text-green-500',
    label: 'Calisiyor',
  },
  understood: {
    icon: CheckCircle,
    color: 'text-green-500',
    bgColor: 'bg-green-100',
    hoverBg: '',
    label: 'Anlasildi',
  },
};

export const KazanimCard = ({ progress, onSelect, onStatusChange }: KazanimCardProps) => {
  const { getIdToken } = useAuth();
  const [showConfirm, setShowConfirm] = useState(false);
  const [isMarking, setIsMarking] = useState(false);
  const [localStatus, setLocalStatus] = useState<KazanimProgressStatus>(progress.status);

  const config = statusConfig[localStatus];
  const Icon = config.icon;
  const canMarkUnderstood = localStatus !== 'understood';

  // Format confidence score as percentage
  const confidencePercent = Math.round(progress.initial_confidence_score * 100);

  const handleIconClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (canMarkUnderstood) {
      setShowConfirm(true);
    }
  };

  const handleConfirm = async () => {
    setIsMarking(true);
    try {
      const token = await getIdToken();
      if (!token) {
        throw new Error('Token alinamadi');
      }

      const response = await fetch(
        `${API_BASE_URL}/users/me/progress/${progress.kazanim_code}/understood`,
        {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            understanding_confidence: 1.0,
            understanding_signals: ['user_confirmed'],
          }),
        }
      );

      if (!response.ok) {
        throw new Error('Islem basarisiz');
      }

      // Update local state immediately for better UX
      setLocalStatus('understood');
      setShowConfirm(false);

      // Notify parent to refetch
      onStatusChange?.();
    } catch (error) {
      console.error('Mark understood error:', error);
      // Could show a toast here
    } finally {
      setIsMarking(false);
    }
  };

  return (
    <>
      <Card
        variant="surface"
        hover
        className="flex items-center gap-4 cursor-pointer transition-all"
        onClick={() => onSelect?.(progress.kazanim_code)}
      >
        {/* Status Icon - Clickable */}
        <button
          onClick={handleIconClick}
          disabled={!canMarkUnderstood}
          className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${config.bgColor} ${
            canMarkUnderstood ? `${config.hoverBg} cursor-pointer` : 'cursor-default'
          }`}
          title={canMarkUnderstood ? 'Anlasildi olarak isaretle' : 'Zaten anlasildi'}
        >
          <Icon className={`w-5 h-5 ${config.color} transition-colors`} />
        </button>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono-custom text-xs font-semibold text-sepia bg-sepia/10 px-2 py-0.5 rounded">
              {progress.kazanim_code}
            </span>
            <span className={`text-xs ${config.color}`}>{config.label}</span>
          </div>
          <p className="text-sm text-ink/80 truncate">{progress.kazanim_description}</p>
          <div className="flex items-center gap-2 mt-1 text-xs text-neutral-400">
            {progress.grade && <span>{progress.grade}. Sinif</span>}
            {progress.subject && (
              <>
                <span className="text-neutral-300">|</span>
                <span>{progress.subject}</span>
              </>
            )}
            <span className="text-neutral-300">|</span>
            <span>%{confidencePercent} eslesme</span>
          </div>
        </div>

        {/* Chevron */}
        <ChevronRight className="w-4 h-4 text-neutral-300 flex-shrink-0" />
      </Card>

      {/* Confirmation Modal */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-enter">
          <div className="bg-paper rounded-2xl shadow-xl max-w-md w-full p-6 animate-enter">
            <div className="flex items-start justify-between mb-4">
              <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                <CheckCircle className="w-6 h-6 text-green-500" />
              </div>
              <button
                onClick={() => setShowConfirm(false)}
                className="text-neutral-400 hover:text-ink transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <h3 className="font-serif-custom text-xl text-ink mb-2">
              Kazanimi Anladiniz mi?
            </h3>
            <p className="text-sm text-neutral-600 mb-2">
              <span className="font-mono-custom text-sepia">{progress.kazanim_code}</span>
            </p>
            <p className="text-sm text-neutral-500 mb-6">{progress.kazanim_description}</p>

            <div className="flex gap-3">
              <Button
                variant="secondary"
                className="flex-1"
                onClick={() => setShowConfirm(false)}
                disabled={isMarking}
              >
                Iptal
              </Button>
              <Button
                className="flex-1"
                onClick={handleConfirm}
                disabled={isMarking}
              >
                {isMarking ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    Isleniyor...
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Evet, Anladim
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default KazanimCard;
