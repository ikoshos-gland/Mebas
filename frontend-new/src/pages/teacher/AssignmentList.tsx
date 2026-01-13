/**
 * Assignment List Page
 * Teachers can view and manage their assignments
 */
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { TeacherLayout } from '../../components/layout';
import type { Assignment, AssignmentListResponse, AssignmentType } from '../../types';
import api from '../../services/api';

const AssignmentList = () => {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<AssignmentType | 'all'>('all');
  const [showInactive, setShowInactive] = useState(false);

  useEffect(() => {
    fetchAssignments();
  }, [filterType, showInactive]);

  const fetchAssignments = async () => {
    try {
      setIsLoading(true);
      const params: Record<string, string | boolean> = {};
      if (filterType !== 'all') params.assignment_type = filterType;
      if (!showInactive) params.is_active = true;

      const response = await api.get<AssignmentListResponse>('/assignments', { params });
      setAssignments(response.data.items);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Odevler yuklenirken hata olustu');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeactivate = async (assignmentId: number) => {
    if (!confirm('Bu odevi pasif yapmak istediginize emin misiniz?')) return;

    try {
      await api.patch(`/assignments/${assignmentId}`, { is_active: false });
      fetchAssignments();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Islem basarisiz');
    }
  };

  const getTypeLabel = (type: AssignmentType) => {
    switch (type) {
      case 'practice': return 'Alistirma';
      case 'exam': return 'Sinav';
      case 'homework': return 'Odev';
      default: return type;
    }
  };

  const getTypeColor = (type: AssignmentType) => {
    switch (type) {
      case 'practice': return 'bg-blue-500/20 text-blue-400';
      case 'exam': return 'bg-red-500/20 text-red-400';
      case 'homework': return 'bg-emerald-500/20 text-emerald-400';
      default: return 'bg-slate-500/20 text-slate-400';
    }
  };

  const createButton = (
    <Link
      to="/odevler/yeni"
      className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
    >
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
      </svg>
      Yeni Odev
    </Link>
  );

  return (
    <TeacherLayout
      title="Odevler"
      breadcrumbs={[
        { label: 'Panel', href: '/ogretmen' },
        { label: 'Odevler' }
      ]}
      actions={createButton}
    >
      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-6">
        <div className="flex gap-2">
          {(['all', 'homework', 'practice', 'exam'] as const).map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filterType === type
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {type === 'all' ? 'Tumu' : getTypeLabel(type as AssignmentType)}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
          <input
            type="checkbox"
            checked={showInactive}
            onChange={(e) => setShowInactive(e.target.checked)}
            className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-blue-600 focus:ring-blue-500"
          />
          <span className="text-sm">Pasif odevleri goster</span>
        </label>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
          {error}
          <button onClick={() => setError(null)} className="ml-4 text-red-300 hover:text-red-200">
            Kapat
          </button>
        </div>
      )}

      {/* Assignments Grid */}
      {isLoading ? (
        <div className="flex justify-center py-16">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      ) : assignments.length === 0 ? (
        <div className="text-center py-16 bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl">
          <div className="w-20 h-20 bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-10 h-10 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
            </svg>
          </div>
          <h3 className="text-xl font-semibold text-white mb-2">Henuz odev yok</h3>
          <p className="text-slate-400 mb-6">Ilk odevinizi olusturarak baslayin</p>
          <Link
            to="/odevler/yeni"
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            Odev Olustur
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {assignments.map((assignment) => (
            <div
              key={assignment.id}
              className={`bg-slate-800/50 backdrop-blur-sm border rounded-xl overflow-hidden transition-all hover:border-blue-500/50 ${
                !assignment.is_active ? 'border-slate-600 opacity-60' : 'border-slate-700'
              }`}
            >
              <div className="p-6">
                <div className="flex items-start justify-between mb-3">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getTypeColor(assignment.assignment_type)}`}>
                    {getTypeLabel(assignment.assignment_type)}
                  </span>
                  {!assignment.is_active && (
                    <span className="px-2 py-1 bg-slate-600 rounded text-xs text-slate-300">
                      Pasif
                    </span>
                  )}
                </div>

                <h3 className="font-semibold text-white text-lg mb-2">
                  {assignment.title}
                </h3>

                {assignment.description && (
                  <p className="text-slate-400 text-sm mb-4 line-clamp-2">
                    {assignment.description}
                  </p>
                )}

                {/* Stats */}
                <div className="flex items-center gap-4 text-sm text-slate-400 mb-4">
                  <div className="flex items-center gap-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                    </svg>
                    <span>{assignment.classroom_count || 0} sinif</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>{assignment.submission_count || 0} teslim</span>
                  </div>
                </div>

                {/* Due Date */}
                {assignment.due_at && (
                  <div className="text-sm text-slate-400 mb-4">
                    <span className="text-slate-500">Son tarih:</span>{' '}
                    {new Date(assignment.due_at).toLocaleDateString('tr-TR')}
                  </div>
                )}

                {/* Target Kazanimlar */}
                {assignment.target_kazanimlar.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-4">
                    {assignment.target_kazanimlar.slice(0, 3).map((code) => (
                      <span key={code} className="px-2 py-0.5 bg-slate-700 rounded text-xs text-slate-300 font-mono">
                        {code}
                      </span>
                    ))}
                    {assignment.target_kazanimlar.length > 3 && (
                      <span className="px-2 py-0.5 bg-slate-700 rounded text-xs text-slate-400">
                        +{assignment.target_kazanimlar.length - 3}
                      </span>
                    )}
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2">
                  <Link
                    to={`/odevler/${assignment.id}`}
                    className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors text-center"
                  >
                    Detaylar
                  </Link>
                  {assignment.is_active && (
                    <button
                      onClick={() => handleDeactivate(assignment.id)}
                      className="p-2 bg-slate-600 hover:bg-slate-500 text-white rounded-lg transition-colors"
                      title="Pasif Yap"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                      </svg>
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </TeacherLayout>
  );
};

export default AssignmentList;
