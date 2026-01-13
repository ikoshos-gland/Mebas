/**
 * Classroom Detail Page
 * View and manage a single classroom, see enrolled students
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { TeacherLayout } from '../../components/layout';
import type { Classroom, StudentEnrollment } from '../../types';
import api from '../../services/api';

interface ClassroomDetailResponse extends Classroom {
  enrollments: StudentEnrollment[];
}

const ClassroomDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [classroom, setClassroom] = useState<ClassroomDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showJoinCode, setShowJoinCode] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);

  useEffect(() => {
    fetchClassroom();
  }, [id]);

  const fetchClassroom = async () => {
    try {
      setIsLoading(true);
      const response = await api.get<ClassroomDetailResponse>(`/classrooms/${id}`);
      setClassroom(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Sinif yuklenirken hata olustu');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegenerateCode = async () => {
    if (!confirm('Yeni katilim kodu olusturmak istediginize emin misiniz? Eski kod artik calismayacak.')) return;

    try {
      setIsRegenerating(true);
      const response = await api.post<{ join_code: string }>(`/classrooms/${id}/regenerate-code`);
      setClassroom(prev => prev ? { ...prev, join_code: response.data.join_code } : null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Kod olusturulurken hata olustu');
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleToggleJoinEnabled = async () => {
    try {
      await api.patch(`/classrooms/${id}`, { join_enabled: !classroom?.join_enabled });
      setClassroom(prev => prev ? { ...prev, join_enabled: !prev.join_enabled } : null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Islem basarisiz');
    }
  };

  const handleRemoveStudent = async (enrollmentId: number) => {
    if (!confirm('Bu ogrenciyi siniftan cikarmak istediginize emin misiniz?')) return;

    try {
      await api.delete(`/classrooms/${id}/enrollments/${enrollmentId}`);
      setClassroom(prev => prev ? {
        ...prev,
        enrollments: prev.enrollments.filter(e => e.id !== enrollmentId),
        student_count: prev.student_count - 1
      } : null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ogrenci cikarilamadi');
    }
  };

  const copyJoinCode = () => {
    if (classroom?.join_code) {
      navigator.clipboard.writeText(classroom.join_code);
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

  if (error || !classroom) {
    return (
      <TeacherLayout>
        <div className="text-center py-20">
          <p className="text-red-400 mb-4">{error || 'Sinif bulunamadi'}</p>
          <button
            onClick={() => navigate('/siniflar')}
            className="text-blue-400 hover:text-blue-300"
          >
            Siniflara Don
          </button>
        </div>
      </TeacherLayout>
    );
  }

  const progressButton = (
    <Link
      to={`/siniflar/${id}/ilerleme`}
      className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
    >
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
      Ilerleme
    </Link>
  );

  return (
    <TeacherLayout
      title={classroom.name}
      breadcrumbs={[
        { label: 'Panel', href: '/ogretmen' },
        { label: 'Siniflar', href: '/siniflar' },
        { label: classroom.name }
      ]}
      actions={progressButton}
    >
        <p className="text-slate-400 -mt-6 mb-8">
          {classroom.grade}. Sinif {classroom.subject && `• ${classroom.subject}`}
        </p>

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
            {error}
            <button onClick={() => setError(null)} className="ml-4 text-red-300 hover:text-red-200">
              Kapat
            </button>
          </div>
        )}

        {/* Classroom Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {/* Join Code Card */}
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Katilim Kodu</h3>
              <button
                onClick={handleToggleJoinEnabled}
                className={`px-3 py-1 rounded-full text-xs font-medium ${
                  classroom.join_enabled
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'bg-red-500/20 text-red-400'
                }`}
              >
                {classroom.join_enabled ? 'Aktif' : 'Kapali'}
              </button>
            </div>
            <div className="flex items-center gap-3">
              <div
                className="flex-1 px-4 py-3 bg-slate-700 rounded-lg font-mono text-xl text-white tracking-widest cursor-pointer"
                onClick={() => setShowJoinCode(!showJoinCode)}
              >
                {showJoinCode ? classroom.join_code : '••••••••'}
              </div>
              <button
                onClick={copyJoinCode}
                className="p-3 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
                title="Kopyala"
              >
                <svg className="w-5 h-5 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
            </div>
            <button
              onClick={handleRegenerateCode}
              disabled={isRegenerating}
              className="mt-4 text-sm text-slate-400 hover:text-slate-300"
            >
              {isRegenerating ? 'Olusturuluyor...' : 'Yeni Kod Olustur'}
            </button>
          </div>

          {/* Stats Card */}
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Istatistikler</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-slate-400">Ogrenci</span>
                <span className="text-white font-medium">{classroom.student_count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Sinif</span>
                <span className="text-white font-medium">{classroom.grade}. Sinif</span>
              </div>
              {classroom.subject && (
                <div className="flex justify-between">
                  <span className="text-slate-400">Ders</span>
                  <span className="text-white font-medium">{classroom.subject}</span>
                </div>
              )}
            </div>
          </div>

          {/* Actions Card */}
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Islemler</h3>
            <div className="space-y-3">
              <Link
                to={`/odevler/yeni?classroom=${id}`}
                className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                Odev Olustur
              </Link>
              <button
                onClick={() => navigate(`/siniflar/${id}/duzenle`)}
                className="w-full px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium transition-colors"
              >
                Sinifi Duzenle
              </button>
            </div>
          </div>
        </div>

        {/* Students List */}
        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-700">
            <h2 className="text-xl font-semibold text-white">Ogrenciler ({classroom.enrollments.length})</h2>
          </div>

          {classroom.enrollments.length === 0 ? (
            <div className="text-center py-16">
              <svg className="w-16 h-16 text-slate-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
              <p className="text-slate-400 mb-2">Henuz ogrenci yok</p>
              <p className="text-slate-500 text-sm">
                Ogrenciler katilim kodunu kullanarak sinifa katilabilir
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-slate-400 text-sm border-b border-slate-700 bg-slate-800/50">
                    <th className="px-6 py-4 font-medium">Ogrenci</th>
                    <th className="px-6 py-4 font-medium">Katilim Tarihi</th>
                    <th className="px-6 py-4 font-medium">Durum</th>
                    <th className="px-6 py-4 font-medium">Islemler</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                  {classroom.enrollments.map((enrollment) => (
                    <tr key={enrollment.id} className="text-slate-300 hover:bg-slate-700/30 transition-colors">
                      <td className="px-6 py-4">
                        <div>
                          <p className="font-medium text-white">{enrollment.student_name || 'Ogrenci'}</p>
                          <p className="text-sm text-slate-400">{enrollment.student_email}</p>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm">
                        {new Date(enrollment.enrolled_at).toLocaleDateString('tr-TR')}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded text-xs ${
                          enrollment.status === 'active'
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : 'bg-slate-500/20 text-slate-400'
                        }`}>
                          {enrollment.status === 'active' ? 'Aktif' : 'Pasif'}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <Link
                            to={`/siniflar/${id}/ogrenci/${enrollment.student_id}`}
                            className="p-2 hover:bg-slate-600 rounded-lg transition-colors"
                            title="Ilerleme"
                          >
                            <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                            </svg>
                          </Link>
                          <button
                            onClick={() => handleRemoveStudent(enrollment.id)}
                            className="p-2 hover:bg-red-500/20 rounded-lg transition-colors"
                            title="Cikar"
                          >
                            <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
    </TeacherLayout>
  );
};

export default ClassroomDetail;
