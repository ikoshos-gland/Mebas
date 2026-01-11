/**
 * ProgressChart - Visual progress ring chart
 *
 * Shows understood vs total kazanimlar as a ring chart
 */
import { Card } from '../common';
import type { ProgressStats } from '../../types';

interface ProgressChartProps {
  stats: ProgressStats | null;
  understoodCount: number;
  totalCount: number;
}

export const ProgressChart = ({ stats, understoodCount, totalCount }: ProgressChartProps) => {
  // Calculate percentage
  const percentage = totalCount > 0 ? Math.round((understoodCount / totalCount) * 100) : 0;

  // SVG ring calculation
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const strokeDasharray = `${(percentage / 100) * circumference} ${circumference}`;

  return (
    <Card variant="surface" className="p-6">
      <h3 className="font-serif-custom text-lg italic text-sepia mb-4">Ilerleme</h3>

      <div className="flex items-center gap-6">
        {/* Ring Chart */}
        <div className="relative w-24 h-24 flex-shrink-0">
          <svg className="w-full h-full transform -rotate-90" viewBox="0 0 96 96">
            {/* Background circle */}
            <circle
              cx="48"
              cy="48"
              r={radius}
              stroke="#e5e5e5"
              strokeWidth="8"
              fill="none"
            />
            {/* Progress circle */}
            <circle
              cx="48"
              cy="48"
              r={radius}
              stroke="#22c55e"
              strokeWidth="8"
              fill="none"
              strokeDasharray={strokeDasharray}
              strokeLinecap="round"
              className="transition-all duration-500"
            />
          </svg>
          {/* Center text */}
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="font-mono-custom text-xl font-bold text-ink">{percentage}%</span>
          </div>
        </div>

        {/* Legend */}
        <div className="space-y-2 flex-1">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-green-500 flex-shrink-0" />
            <span className="text-sm text-ink">{understoodCount} Anlasildi</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-amber-500 flex-shrink-0" />
            <span className="text-sm text-ink">{stats?.in_progress_count || 0} Calisiyor</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-stone-300 flex-shrink-0" />
            <span className="text-sm text-ink">
              {totalCount - understoodCount - (stats?.in_progress_count || 0)} Takipte
            </span>
          </div>
        </div>
      </div>

      {/* This week stats */}
      {stats && (
        <div className="mt-4 pt-4 border-t border-stone-200">
          <div className="flex justify-between text-sm">
            <span className="text-neutral-500">Bu hafta</span>
            <span className="font-medium text-green-600">+{stats.this_week_understood}</span>
          </div>
          {stats.streak_days > 0 && (
            <div className="flex justify-between text-sm mt-1">
              <span className="text-neutral-500">Seri</span>
              <span className="font-medium text-orange-500">{stats.streak_days} gun</span>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {totalCount === 0 && (
        <div className="mt-4 text-center text-sm text-neutral-400">
          Sohbette soru sordukca kazanimlariniz burada gorunecek
        </div>
      )}
    </Card>
  );
};

export default ProgressChart;
