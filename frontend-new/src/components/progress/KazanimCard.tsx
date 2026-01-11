/**
 * KazanimCard - Individual kazanim progress card
 *
 * Displays a single kazanim with its status (tracked, in_progress, understood)
 */
import { CheckCircle, Circle, Clock, ChevronRight } from 'lucide-react';
import { Card } from '../common';
import type { KazanimProgress, KazanimProgressStatus } from '../../types';

interface KazanimCardProps {
  progress: KazanimProgress;
  onSelect?: (code: string) => void;
}

const statusConfig: Record<
  KazanimProgressStatus,
  { icon: typeof CheckCircle; color: string; bgColor: string; label: string }
> = {
  tracked: {
    icon: Circle,
    color: 'text-neutral-400',
    bgColor: 'bg-stone-100',
    label: 'Takipte',
  },
  in_progress: {
    icon: Clock,
    color: 'text-amber-500',
    bgColor: 'bg-amber-100',
    label: 'Calisiyor',
  },
  understood: {
    icon: CheckCircle,
    color: 'text-green-500',
    bgColor: 'bg-green-100',
    label: 'Anlasildi',
  },
};

export const KazanimCard = ({ progress, onSelect }: KazanimCardProps) => {
  const config = statusConfig[progress.status];
  const Icon = config.icon;

  // Format confidence score as percentage
  const confidencePercent = Math.round(progress.initial_confidence_score * 100);

  return (
    <Card
      variant="surface"
      hover
      className="flex items-center gap-4 cursor-pointer transition-all"
      onClick={() => onSelect?.(progress.kazanim_code)}
    >
      {/* Status Icon */}
      <div
        className={`w-10 h-10 rounded-full flex items-center justify-center ${config.bgColor}`}
      >
        <Icon className={`w-5 h-5 ${config.color}`} />
      </div>

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
  );
};

export default KazanimCard;
