/**
 * RecommendationsList - AI-suggested prerequisite kazanimlar
 *
 * Shows recommendations for missing prerequisites based on tracked items
 */
import { AlertCircle, AlertTriangle, Info, ChevronRight } from 'lucide-react';
import { Card } from '../common';
import type { PrerequisiteRecommendation, RecommendationPriority } from '../../types';

interface RecommendationsListProps {
  recommendations: PrerequisiteRecommendation[];
  onSelect?: (code: string) => void;
}

const priorityConfig: Record<
  RecommendationPriority,
  { icon: typeof AlertCircle; color: string; bgColor: string; label: string }
> = {
  critical: {
    icon: AlertCircle,
    color: 'text-red-500',
    bgColor: 'bg-red-100',
    label: 'Kritik',
  },
  important: {
    icon: AlertTriangle,
    color: 'text-amber-500',
    bgColor: 'bg-amber-100',
    label: 'Onemli',
  },
  helpful: {
    icon: Info,
    color: 'text-blue-500',
    bgColor: 'bg-blue-100',
    label: 'Faydali',
  },
};

export const RecommendationsList = ({ recommendations, onSelect }: RecommendationsListProps) => {
  if (recommendations.length === 0) {
    return null;
  }

  return (
    <Card variant="surface" className="p-6">
      <h3 className="font-serif-custom text-lg italic text-sepia mb-4">Oneriler</h3>
      <p className="text-sm text-neutral-500 mb-4">
        Bu kazanimlar, takip ettiginiz konular icin on kosul niteliginde
      </p>

      <div className="space-y-3">
        {recommendations.map((rec) => {
          const config = priorityConfig[rec.priority];
          const Icon = config.icon;

          return (
            <div
              key={rec.kazanim_code}
              className="flex items-start gap-3 p-3 rounded-lg bg-stone-50 hover:bg-stone-100 cursor-pointer transition-colors"
              onClick={() => onSelect?.(rec.kazanim_code)}
            >
              {/* Priority Icon */}
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${config.bgColor}`}
              >
                <Icon className={`w-4 h-4 ${config.color}`} />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono-custom text-xs font-semibold text-sepia bg-sepia/10 px-2 py-0.5 rounded">
                    {rec.kazanim_code}
                  </span>
                  <span className={`text-xs ${config.color}`}>{config.label}</span>
                </div>
                <p className="text-sm text-ink/80 line-clamp-2">{rec.kazanim_description}</p>
                <p className="text-xs text-neutral-400 mt-1">{rec.reason}</p>
                {rec.related_to.length > 0 && (
                  <div className="flex items-center gap-1 mt-1 text-xs text-neutral-400">
                    <span>Iliskili:</span>
                    {rec.related_to.slice(0, 2).map((code, i) => (
                      <span key={code} className="font-mono-custom">
                        {code}
                        {i < Math.min(rec.related_to.length - 1, 1) && ','}
                      </span>
                    ))}
                    {rec.related_to.length > 2 && <span>+{rec.related_to.length - 2}</span>}
                  </div>
                )}
              </div>

              {/* Chevron */}
              <ChevronRight className="w-4 h-4 text-neutral-300 flex-shrink-0 mt-1" />
            </div>
          );
        })}
      </div>
    </Card>
  );
};

export default RecommendationsList;
