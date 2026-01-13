/**
 * Assignment Detail Page
 * View assignment details and distribution status
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { TeacherLayout } from '../../components/layout';
import type { Assignment, AssignmentType, Classroom, ClassroomListResponse } from '../../types';
import api from '../../services/api';

interface AssignmentDetailResponse extends Assignment {
  distributions: {
    classroom_id: number;
    classroom_name: string;
    student_count: number;
    submitted_count: number;
    due_at?: string;
  }[];
}

const AssignmentDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [assignment, setAssignment] = useState<AssignmentDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Add classroom modal
  const [showAddModal, setShowAddModal] = useState(false);
  const [availableClassrooms, setAvailableClassrooms] = useState<Classroom[]>([]);
  const [selectedClassrooms, setSelectedClassrooms] = useState<number[]>([]);
  const [isAdding, setIsAdding] = useState(false);

  useEffect(() => {
    fetchAssignment();
  }, [id]);

  const fetchAssignment = async () => {
    try {
      setIsLoading(true);
      const response = await api.get<AssignmentDetailResponse>(`/assignments/${id}`);
      setAssignment(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Odev yuklenirken hata olustu');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchAvailableClassrooms = async () => {
    try {
      const response = await api.get<ClassroomListResponse>('/classrooms');
      const distributedIds = assignment?.distributions.map(d => d.classroom_id) || [];
      setAvailableClassrooms(
        response.data.items.filter(c => !distributedIds.includes(c.id))
      );
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Siniflar yuklenirken hata olustu');
    }
  };

  const handleOpenAddModal = () => {
    fetchAvailableClassrooms();
    setSelectedClassrooms([]);
    setShowAddModal(true);
  };

  const handleAddClassrooms = async () => {
    if (selectedClassrooms.length === 0) return;

    try {
      setIsAdding(true);
      await api.post(`/assignments/${id}/distribute`, {
        classroom_ids: selectedClassrooms
      });
      setShowAddModal(false);
      fetchAssignment();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Siniflar eklenirken hata olustu');
    } finally {
      setIsAdding(false);
    }
  };

  const handleToggleActive = async () => {
    try {
      await api.patch(`/assignments/${id}`, { is_active: !assignment?.is_active });
      fetchAssignment();
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

  if (isLoading) {
    return (
      <TeacherLayout>
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      </TeacherLayout>
    );
  }

  if (error || !assignment) {
    return (
      <TeacherLayout>
        <div className="text-center py-20">
          <p className="text-red-400 mb-4">{error || 'Odev bulunamadi'}</p>
          <button
            onClick={() => navigate('/odevler')}
            className="text-blue-400 hover:text-blue-300"
          >
            Odevlere Don
          </button>
        </div>
      </TeacherLayout>
    );
  }

  const totalStudents = assignment.distributions.reduce((sum, d) => sum + d.student_count, 0);
  const totalSubmissions = assignment.distributions.reduce((sum, d) => sum + d.submitted_count, 0);

  const actionButtons = (
    <div className="flex gap-2">
      <button
        onClick={handleOpenAddModal}
        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
        </svg>
        Sinif Ekle
      </button>
      <button
        onClick={handleToggleActive}
        className={`px-4 py-2 rounded-lg font-medium transition-colors ${
          assignment.is_active
            ? 'bg-slate-600 hover:bg-slate-500 text-white'
            : 'bg-emerald-600 hover:bg-emerald-700 text-white'
        }`}
      >
        {assignment.is_active ? 'Pasif Yap' : 'Aktif Yap'}
      </button>
    </div>
  );

  return (
    <TeacherLayout
      title={assignment.title}
      breadcrumbs={[
        { label: 'Panel', href: '/ogretmen' },
        { label: 'Odevler', href: '/odevler' },
        { label: assignment.title }
      ]}
      actions={actionButtons}
    >
      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
          {error}
          <button onClick={() => setError(null)} className="ml-4 text-red-300 hover:text-red-200">
            Kapat
          </button>
        </div>
      )}

      {/* Assignment Info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2 bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getTypeColor(assignment.assignment_type)}`}>
                {getTypeLabel(assignment.assignment_type)}
              </span>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                assignment.is_active
                  ? 'bg-emerald-500/20 text-emerald-400'
                  : 'bg-slate-500/20 text-slate-400'
              }`}>
                {assignment.is_active ? 'Aktif' : 'Pasif'}
              </span>
            </div>
          </div>

          {assignment.description && (
            <p className="text-slate-300 mb-6">{assignment.description}</p>
          )}

          {/* Target Kazanimlar */}
          {assignment.target_kazanimlar.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-slate-400 mb-2">Hedef Kazanimlar</h3>
              <div className="flex flex-wrap gap-2">
                {assignment.target_kazanimlar.map((code) => (
                  <span key={code} className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-full text-sm font-mono">
                    {code}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Dates */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-slate-400">Olusturulma</p>
              <p className="text-white">
                {new Date(assignment.created_at).toLocaleDateString('tr-TR')}
              </p>
            </div>
            {assignment.due_at && (
              <div>
                <p className="text-slate-400">Son Tarih</p>
                <p className="text-white">
                  {new Date(assignment.due_at).toLocaleString('tr-TR')}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="space-y-4">
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
            <p className="text-slate-400 text-sm">Dagitilan Sinif</p>
            <p className="text-3xl font-bold text-white mt-1">{assignment.distributions.length}</p>
          </div>
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
            <p className="text-slate-400 text-sm">Toplam Ogrenci</p>
            <p className="text-3xl font-bold text-white mt-1">{totalStudents}</p>
          </div>
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
            <p className="text-slate-400 text-sm">Teslim Edilen</p>
            <p className="text-3xl font-bold text-emerald-400 mt-1">
              {totalSubmissions}
              <span className="text-lg text-slate-400 ml-2">
                / {totalStudents}
              </span>
            </p>
          </div>
        </div>
      </div>

      {/* Distributions */}
      <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-white">Dagitim Durumu</h2>
        </div>

        {assignment.distributions.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-slate-400 mb-4">Bu odev henuz hicbir sinifa dagitilmamis</p>
            <button
              onClick={handleOpenAddModal}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              Sinif Ekle
            </button>
          </div>
        ) : (
          <div className="divide-y divide-slate-700">
            {assignment.distributions.map((dist) => {
              const progress = dist.student_count > 0
                ? (dist.submitted_count / dist.student_count) * 100
                : 0;

              return (
                <div key={dist.classroom_id} className="px-6 py-4">
                  <div className="flex items-center justify-between mb-2">
                    <Link
                      to={`/siniflar/${dist.classroom_id}`}
                      className="font-medium text-white hover:text-blue-400 transition-colors"
                    >
                      {dist.classroom_name}
                    </Link>
                    <span className="text-sm text-slate-400">
                      {dist.submitted_count} / {dist.student_count} teslim
                    </span>
                  </div>
                  <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-emerald-500 transition-all"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  {dist.due_at && (
                    <p className="text-xs text-slate-500 mt-2">
                      Son tarih: {new Date(dist.due_at).toLocaleString('tr-TR')}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Add Classroom Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-xl max-w-lg w-full p-6 max-h-[80vh] overflow-y-auto">
            <h2 className="text-xl font-semibold text-white mb-6">Sinif Ekle</h2>

            {availableClassrooms.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-slate-400">Tum siniflariniza bu odev dagitilmis</p>
              </div>
            ) : (
              <div className="space-y-3 mb-6">
                {availableClassrooms.map((classroom) => (
                  <label
                    key={classroom.id}
                    className={`flex items-center gap-4 p-4 rounded-lg border cursor-pointer transition-colors ${
                      selectedClassrooms.includes(classroom.id)
                        ? 'border-blue-500 bg-blue-500/10'
                        : 'border-slate-600 bg-slate-700/50 hover:bg-slate-700'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedClassrooms.includes(classroom.id)}
                      onChange={() => {
                        if (selectedClassrooms.includes(classroom.id)) {
                          setSelectedClassrooms(selectedClassrooms.filter(id => id !== classroom.id));
                        } else {
                          setSelectedClassrooms([...selectedClassrooms, classroom.id]);
                        }
                      }}
                      className="w-5 h-5 rounded border-slate-500 bg-slate-600 text-blue-600 focus:ring-blue-500"
                    />
                    <div className="flex-1">
                      <p className="font-medium text-white">{classroom.name}</p>
                      <p className="text-sm text-slate-400">
                        {classroom.grade}. Sinif • {classroom.student_count} ogrenci
                      </p>
                    </div>
                  </label>
                ))}
              </div>
            )}

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium transition-colors"
              >
                Iptal
              </button>
              <button
                type="button"
                onClick={handleAddClassrooms}
                disabled={selectedClassrooms.length === 0 || isAdding}
                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
              >
                {isAdding ? 'Ekleniyor...' : `${selectedClassrooms.length} Sinif Ekle`}
              </button>
            </div>
          </div>
        </div>
      )}
    </TeacherLayout>
  );
};

export default AssignmentDetail;
