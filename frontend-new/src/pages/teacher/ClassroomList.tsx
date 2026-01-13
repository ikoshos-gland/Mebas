/**
 * Classroom List & Management Page
 * Teachers can view, create, and manage their classrooms
 */
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { TeacherLayout } from '../../components/layout';
import type { Classroom, ClassroomListResponse, CreateClassroomRequest } from '../../types';
import api from '../../services/api';

const ClassroomList = () => {
  const [classrooms, setClassrooms] = useState<Classroom[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [includeArchived, setIncludeArchived] = useState(false);

  // Create form state
  const [newClassroom, setNewClassroom] = useState<CreateClassroomRequest>({
    name: '',
    grade: 9,
    subject: '',
  });
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    fetchClassrooms();
  }, [includeArchived]);

  const fetchClassrooms = async () => {
    try {
      setIsLoading(true);
      const response = await api.get<ClassroomListResponse>('/classrooms', {
        params: { include_archived: includeArchived }
      });
      setClassrooms(response.data.items);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Siniflar yuklenirken hata olustu');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateClassroom = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newClassroom.name.trim()) return;

    try {
      setIsCreating(true);
      const response = await api.post<Classroom>('/classrooms', newClassroom);
      setClassrooms([response.data, ...classrooms]);
      setShowCreateModal(false);
      setNewClassroom({ name: '', grade: 9, subject: '' });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Sinif olusturulurken hata olustu');
    } finally {
      setIsCreating(false);
    }
  };

  const handleArchive = async (classroomId: number) => {
    if (!confirm('Bu sinifi arsivlemek istediginize emin misiniz?')) return;

    try {
      await api.post(`/classrooms/${classroomId}/archive`);
      fetchClassrooms();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Arsivleme hatasi');
    }
  };

  const copyJoinCode = (code: string) => {
    navigator.clipboard.writeText(code);
    // You could add a toast notification here
  };

  const createButton = (
    <button
      onClick={() => setShowCreateModal(true)}
      className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
    >
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
      </svg>
      Yeni Sinif
    </button>
  );

  return (
    <TeacherLayout
      title="Siniflarim"
      breadcrumbs={[
        { label: 'Panel', href: '/ogretmen' },
        { label: 'Siniflar' }
      ]}
      actions={createButton}
    >
        {/* Filters */}
        <div className="mb-6">
          <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(e) => setIncludeArchived(e.target.checked)}
              className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm">Arsivlenmis siniflari goster</span>
          </label>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
            {error}
            <button
              onClick={() => setError(null)}
              className="ml-4 text-red-300 hover:text-red-200"
            >
              Kapat
            </button>
          </div>
        )}

        {/* Classrooms Grid */}
        {isLoading ? (
          <div className="flex justify-center py-16">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
        ) : classrooms.length === 0 ? (
          <div className="text-center py-16 bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl">
            <div className="w-20 h-20 bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-10 h-10 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Henuz sinif yok</h3>
            <p className="text-slate-400 mb-6">Ilk sinifinizi olusturarak baslayin</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              Sinif Olustur
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {classrooms.map((classroom) => (
              <div
                key={classroom.id}
                className={`bg-slate-800/50 backdrop-blur-sm border rounded-xl overflow-hidden transition-all hover:border-blue-500/50 ${
                  classroom.is_archived ? 'border-slate-600 opacity-60' : 'border-slate-700'
                }`}
              >
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="font-semibold text-white text-lg">
                        {classroom.name}
                      </h3>
                      <p className="text-slate-400 text-sm mt-1">
                        {classroom.grade}. Sinif {classroom.subject && `- ${classroom.subject}`}
                      </p>
                    </div>
                    {classroom.is_archived && (
                      <span className="px-2 py-1 bg-slate-600 rounded text-xs text-slate-300">
                        Arsivlenmis
                      </span>
                    )}
                  </div>

                  {/* Join Code */}
                  <div className="bg-slate-700/50 rounded-lg p-3 mb-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-xs text-slate-400">Katilim Kodu</p>
                        <p className="font-mono text-lg text-blue-400 font-bold">
                          {classroom.join_code}
                        </p>
                      </div>
                      <button
                        onClick={() => copyJoinCode(classroom.join_code)}
                        className="p-2 hover:bg-slate-600 rounded-lg transition-colors"
                        title="Kodu Kopyala"
                      >
                        <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                      </button>
                    </div>
                    {!classroom.join_enabled && (
                      <p className="text-amber-400 text-xs mt-2">Katilim kapali</p>
                    )}
                  </div>

                  {/* Stats */}
                  <div className="flex items-center gap-4 text-sm text-slate-400 mb-4">
                    <div className="flex items-center gap-1">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                      </svg>
                      <span>{classroom.student_count} ogrenci</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2">
                    <Link
                      to={`/siniflar/${classroom.id}`}
                      className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors text-center"
                    >
                      Detaylar
                    </Link>
                    <Link
                      to={`/siniflar/${classroom.id}/ilerleme`}
                      className="flex-1 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium transition-colors text-center"
                    >
                      Ilerleme
                    </Link>
                    {!classroom.is_archived && (
                      <button
                        onClick={() => handleArchive(classroom.id)}
                        className="p-2 bg-slate-600 hover:bg-slate-500 text-white rounded-lg transition-colors"
                        title="Arsivle"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                        </svg>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Create Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-slate-800 border border-slate-700 rounded-xl max-w-md w-full p-6">
              <h2 className="text-xl font-semibold text-white mb-6">Yeni Sinif Olustur</h2>

              <form onSubmit={handleCreateClassroom} className="space-y-4">
                {/* Name */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Sinif Adi *
                  </label>
                  <input
                    type="text"
                    value={newClassroom.name}
                    onChange={(e) => setNewClassroom({ ...newClassroom, name: e.target.value })}
                    placeholder="ornegin: 10-A Matematik"
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                    required
                  />
                </div>

                {/* Grade */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Sinif Seviyesi *
                  </label>
                  <select
                    value={newClassroom.grade}
                    onChange={(e) => setNewClassroom({ ...newClassroom, grade: parseInt(e.target.value) })}
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                  >
                    {[9, 10, 11, 12].map((g) => (
                      <option key={g} value={g}>{g}. Sinif</option>
                    ))}
                  </select>
                </div>

                {/* Subject */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Ders (Opsiyonel)
                  </label>
                  <input
                    type="text"
                    value={newClassroom.subject || ''}
                    onChange={(e) => setNewClassroom({ ...newClassroom, subject: e.target.value })}
                    placeholder="ornegin: Matematik"
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </div>

                {/* Buttons */}
                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium transition-colors"
                  >
                    Iptal
                  </button>
                  <button
                    type="submit"
                    disabled={isCreating || !newClassroom.name.trim()}
                    className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
                  >
                    {isCreating ? 'Olusturuluyor...' : 'Olustur'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
    </TeacherLayout>
  );
};

export default ClassroomList;
