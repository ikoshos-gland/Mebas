/**
 * Student Progress Detail Page
 * Shows individual student's kazanim progress against full curriculum
 */
import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Download } from 'lucide-react';
import { TeacherLayout } from '../../components/layout';
import type { StudentProgressDetailResponse, StudentKazanimStatus } from '../../types';
import api from '../../services/api';

// Status colors matching design requirements
const STATUS_CONFIG: Record<StudentKazanimStatus, { bg: string; text: string; icon: string; label: string }> = {
  understood: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', icon: '✓', label: 'Anladi' },
  in_progress: { bg: 'bg-amber-500/20', text: 'text-amber-400', icon: '◐', label: 'Calisiyor' },
  tracked: { bg: 'bg-blue-500/20', text: 'text-blue-400', icon: '◉', label: 'Takipte' },
  not_started: { bg: 'bg-slate-500/20', text: 'text-slate-400', icon: '○', label: 'Baslamadi' }
};

const StudentProgressDetail = () => {
  const { id: classroomId, studentId } = useParams<{ id: string; studentId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<StudentProgressDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    fetchProgress();
  }, [classroomId, studentId]);

  const fetchProgress = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await api.get<StudentProgressDetailResponse>(
        `/classrooms/${classroomId}/progress/${studentId}`
      );
      setData(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ilerleme verileri yuklenirken hata olustu');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportCSV = async () => {
    try {
      setIsExporting(true);
      const response = await api.get(`/classrooms/${classroomId}/progress/${studentId}/export/csv`, {
        responseType: 'blob',
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `ogrenci_ilerleme_${studentId}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export error:', err);
    } finally {
      setIsExporting(false);
    }
  };

  // Filter and search kazanimlar
  const filteredKazanimlar = useMemo(() => {
    if (!data) return [];

    return data.curriculum.filter(k => {
      // Search filter
      const matchesSearch = searchTerm === '' ||
        k.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
        k.description.toLowerCase().includes(searchTerm.toLowerCase());

      // Status filter
      const status = data.progress_by_code[k.code]?.status || 'not_started';
      const matchesStatus = statusFilter === 'all' || status === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [data, searchTerm, statusFilter]);

  // Get status for a kazanim
  const getStatus = (code: string): StudentKazanimStatus => {
    return (data?.progress_by_code[code]?.status as StudentKazanimStatus) || 'not_started';
  };

  // Format date
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('tr-TR', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  };

  // Loading state
  if (isLoading) {
    return (
      <TeacherLayout>
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      </TeacherLayout>
    );
  }

  // Error state
  if (error || !data) {
    return (
      <TeacherLayout>
        <div className="text-center py-20">
          <p className="text-red-400 mb-4">{error || 'Veri bulunamadi'}</p>
          <button
            onClick={() => navigate(`/siniflar/${classroomId}`)}
            className="text-blue-400 hover:text-blue-300"
          >
            Sinifa Don
          </button>
        </div>
      </TeacherLayout>
    );
  }

  const completionPercentage = data.summary.total > 0
    ? Math.round((data.summary.understood / data.summary.total) * 100)
    : 0;

  return (
    <TeacherLayout
      title={`${data.student.full_name} - Kazanim Ilerlemesi`}
      breadcrumbs={[
        { label: 'Panel', href: '/ogretmen' },
        { label: 'Siniflar', href: '/siniflar' },
        { label: data.classroom.name, href: `/siniflar/${classroomId}` },
        { label: data.student.full_name }
      ]}
    >
      {/* Header with export button */}
      <div className="flex items-center justify-between -mt-6 mb-8">
        <p className="text-slate-400">
          {data.classroom.grade}. Sinif {data.classroom.subject && `• ${data.classroom.subject}`}
        </p>
        <button
          onClick={handleExportCSV}
          disabled={isExporting}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white text-sm rounded-lg transition-colors"
        >
          <Download className="w-4 h-4" />
          {isExporting ? 'Indiriliyor...' : 'CSV Indir'}
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-4">
          <p className="text-slate-400 text-sm mb-1">Toplam</p>
          <p className="text-2xl font-bold text-white">{data.summary.total}</p>
        </div>
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4">
          <p className="text-emerald-400 text-sm mb-1">Anladi</p>
          <p className="text-2xl font-bold text-emerald-400">{data.summary.understood}</p>
        </div>
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
          <p className="text-amber-400 text-sm mb-1">Calisiyor</p>
          <p className="text-2xl font-bold text-amber-400">{data.summary.in_progress}</p>
        </div>
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4">
          <p className="text-blue-400 text-sm mb-1">Takipte</p>
          <p className="text-2xl font-bold text-blue-400">{data.summary.tracked}</p>
        </div>
        <div className="bg-slate-500/10 border border-slate-500/20 rounded-xl p-4">
          <p className="text-slate-400 text-sm mb-1">Baslamadi</p>
          <p className="text-2xl font-bold text-slate-400">{data.summary.not_started}</p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6 mb-8">
        <div className="flex items-center justify-between mb-3">
          <span className="text-slate-300">Tamamlanma Orani</span>
          <span className="text-white font-semibold">{completionPercentage}%</span>
        </div>
        <div className="w-full bg-slate-700 rounded-full h-3">
          <div
            className="bg-emerald-500 h-3 rounded-full transition-all duration-500"
            style={{ width: `${completionPercentage}%` }}
          />
        </div>
      </div>

      {/* Filters */}
      <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-4 mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                placeholder="Kazanim kodu veya aciklama ara..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
          >
            <option value="all">Tum Durumlar</option>
            <option value="understood">Anladi</option>
            <option value="in_progress">Calisiyor</option>
            <option value="tracked">Takipte</option>
            <option value="not_started">Baslamadi</option>
          </select>
        </div>
      </div>

      {/* Color Legend */}
      <div className="flex flex-wrap gap-4 mb-6 text-sm">
        {(Object.entries(STATUS_CONFIG) as [StudentKazanimStatus, typeof STATUS_CONFIG[StudentKazanimStatus]][]).map(([status, config]) => (
          <div key={status} className="flex items-center gap-2">
            <span className={`px-2 py-1 rounded ${config.bg} ${config.text}`}>
              {config.icon}
            </span>
            <span className="text-slate-400">{config.label}</span>
          </div>
        ))}
      </div>

      {/* Kazanim List */}
      <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-700">
          <h2 className="text-xl font-semibold text-white">
            Kazanimlar ({filteredKazanimlar.length})
          </h2>
        </div>

        {filteredKazanimlar.length === 0 ? (
          <div className="text-center py-16">
            <svg className="w-16 h-16 text-slate-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <p className="text-slate-400 mb-2">Sonuc bulunamadi</p>
            <p className="text-slate-500 text-sm">Arama kriterlerinizi degistirmeyi deneyin</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-slate-400 text-sm border-b border-slate-700 bg-slate-800/50">
                  <th className="px-6 py-4 font-medium">Kod</th>
                  <th className="px-6 py-4 font-medium">Kazanim</th>
                  <th className="px-6 py-4 font-medium">Durum</th>
                  <th className="px-6 py-4 font-medium">Guven</th>
                  <th className="px-6 py-4 font-medium">Tarih</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {filteredKazanimlar.map((kazanim) => {
                  const status = getStatus(kazanim.code);
                  const progress = data.progress_by_code[kazanim.code];
                  const config = STATUS_CONFIG[status];

                  return (
                    <tr key={kazanim.code} className="text-slate-300 hover:bg-slate-700/30 transition-colors">
                      <td className="px-6 py-4">
                        <span className="px-2 py-1 bg-slate-700 rounded text-xs font-mono text-white">
                          {kazanim.code}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <p className="text-white">{kazanim.description}</p>
                        {kazanim.title && (
                          <p className="text-sm text-slate-400 mt-1">{kazanim.title}</p>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-3 py-1 rounded text-xs font-medium ${config.bg} ${config.text}`}>
                          {config.icon} {config.label}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm">
                        {progress?.understanding_confidence != null ? (
                          <span className="text-emerald-400">
                            {Math.round(progress.understanding_confidence * 100)}%
                          </span>
                        ) : progress?.initial_confidence_score != null ? (
                          <span className="text-blue-400">
                            {Math.round(progress.initial_confidence_score * 100)}%
                          </span>
                        ) : (
                          <span className="text-slate-500">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-400">
                        {status === 'understood' && progress?.understood_at
                          ? formatDate(progress.understood_at)
                          : progress?.tracked_at
                            ? formatDate(progress.tracked_at)
                            : '-'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </TeacherLayout>
  );
};

export default StudentProgressDetail;
