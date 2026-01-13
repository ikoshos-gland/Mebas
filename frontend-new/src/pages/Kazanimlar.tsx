import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Target,
  ChevronLeft,
  Loader2,
  Search,
  Filter,
  CheckCircle,
  Clock,
  Circle,
} from 'lucide-react';
import { Header } from '../components/layout/Header';
import { Card, Button } from '../components/common';
import { useProgress } from '../hooks/useProgress';
import { KazanimCard } from '../components/progress';
import type { KazanimProgressStatus } from '../types';

const statusFilters: { value: KazanimProgressStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'Tumu' },
  { value: 'tracked', label: 'Takipte' },
  { value: 'in_progress', label: 'Calisiyor' },
  { value: 'understood', label: 'Anlasildi' },
];

const Kazanimlar = () => {
  const { progress, isLoading, understoodCount, trackedCount, inProgressCount, refetch } = useProgress();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<KazanimProgressStatus | 'all'>('all');

  // Filter progress based on search and status
  const filteredProgress = progress.filter((item) => {
    const matchesSearch =
      searchQuery === '' ||
      item.kazanim_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.kazanim_description.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus = statusFilter === 'all' || item.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  // Group by grade
  const groupedByGrade = filteredProgress.reduce(
    (acc, item) => {
      const grade = item.grade || 0;
      if (!acc[grade]) {
        acc[grade] = [];
      }
      acc[grade].push(item);
      return acc;
    },
    {} as Record<number, typeof progress>
  );

  const sortedGrades = Object.keys(groupedByGrade)
    .map(Number)
    .sort((a, b) => b - a);

  return (
    <div className="min-h-screen bg-canvas">
      <Header transparent={false} />

      <main className="pt-24 pb-12 px-4 md:px-8">
        <div className="max-w-4xl mx-auto">
          {/* Back Button & Title */}
          <div className="mb-6 animate-enter">
            <Link
              to="/panel"
              className="inline-flex items-center gap-2 text-sm text-neutral-500 hover:text-ink transition-colors mb-4"
            >
              <ChevronLeft className="w-4 h-4" />
              Panele Don
            </Link>
            <div className="flex items-center justify-between">
              <div>
                <h1 className="font-serif-custom text-3xl text-ink mb-2">Kazanim Takibi</h1>
                <p className="text-neutral-600">
                  Ogrenme yolculugunuzdaki tum kazanimlarinizi buradan takip edebilirsiniz.
                </p>
              </div>
              <div className="hidden md:flex items-center gap-6 text-sm">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-green-500" />
                  <span className="text-neutral-600">{understoodCount} Anlasildi</span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-amber-500" />
                  <span className="text-neutral-600">{inProgressCount} Calisiyor</span>
                </div>
                <div className="flex items-center gap-2">
                  <Circle className="w-4 h-4 text-neutral-400" />
                  <span className="text-neutral-600">{trackedCount} Takipte</span>
                </div>
              </div>
            </div>
          </div>

          {/* Search & Filters */}
          <div className="flex flex-col sm:flex-row gap-4 mb-6 animate-enter animate-delay-100">
            {/* Search */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
              <input
                type="text"
                placeholder="Kazanim ara..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input-field pl-10"
              />
            </div>

            {/* Status Filter */}
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-neutral-400" />
              <div className="flex gap-1">
                {statusFilters.map((filter) => (
                  <button
                    key={filter.value}
                    onClick={() => setStatusFilter(filter.value)}
                    className={`px-3 py-1.5 text-xs rounded-full transition-all ${
                      statusFilter === filter.value
                        ? 'bg-ink text-paper'
                        : 'bg-stone-100 text-neutral-600 hover:bg-stone-200'
                    }`}
                  >
                    {filter.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Content */}
          {isLoading ? (
            <Card variant="outlined" className="flex items-center justify-center py-16">
              <Loader2 className="w-8 h-8 text-sepia animate-spin" />
            </Card>
          ) : filteredProgress.length > 0 ? (
            <div className="space-y-8">
              {sortedGrades.map((grade) => (
                <div key={grade} className="animate-enter">
                  <h2 className="font-serif-custom text-lg italic text-sepia mb-4">
                    {grade > 0 ? `${grade}. Sinif` : 'Sinif Belirtilmemis'}
                    <span className="text-sm text-neutral-400 ml-2">
                      ({groupedByGrade[grade].length} kazanim)
                    </span>
                  </h2>
                  <div className="space-y-3">
                    {groupedByGrade[grade].map((item, index) => (
                      <div
                        key={item.kazanim_code}
                        className="animate-enter"
                        style={{ animationDelay: `${index * 0.05}s` }}
                      >
                        <KazanimCard progress={item} onStatusChange={refetch} />
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : progress.length > 0 ? (
            <Card variant="outlined" className="text-center py-16">
              <Search className="w-12 h-12 text-neutral-300 mx-auto mb-4" />
              <p className="text-neutral-500 mb-2">Aramanizla eslesen kazanim bulunamadi</p>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setSearchQuery('');
                  setStatusFilter('all');
                }}
              >
                Filtreleri Temizle
              </Button>
            </Card>
          ) : (
            <Card variant="outlined" className="text-center py-16">
              <Target className="w-12 h-12 text-neutral-300 mx-auto mb-4" />
              <p className="text-neutral-500 mb-2">Henuz takip edilen kazanim yok</p>
              <p className="text-sm text-neutral-400 mb-4">
                Sohbette soru sordukca yuksek guvenli kazanimlar otomatik olarak buraya eklenir
              </p>
              <Link to="/sohbet">
                <Button size="sm">Ilk Sorunuzu Sorun</Button>
              </Link>
            </Card>
          )}
        </div>
      </main>
    </div>
  );
};

export default Kazanimlar;
