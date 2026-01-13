/**
 * My Classrooms Page
 * Students view their enrolled classrooms
 */
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../../services/api';

interface EnrolledClassroom {
  id: number;
  classroom_id: number;
  classroom_name: string;
  teacher_name: string;
  grade: number;
  subject: string | null;
  status: string;
  enrolled_at: string;
}

const MyClassrooms = () => {
  const [classrooms, setClassrooms] = useState<EnrolledClassroom[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchClassrooms();
  }, []);

  const fetchClassrooms = async () => {
    try {
      setIsLoading(true);
      const response = await api.get<EnrolledClassroom[]>('/classrooms/enrolled');
      setClassrooms(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Siniflar yuklenirken hata olustu');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLeaveClassroom = async (enrollmentId: number, classroomName: string) => {
    if (!confirm(`${classroomName} sinifindan ayrilmak istediginize emin misiniz?`)) return;

    try {
      await api.delete(`/classrooms/enrollments/${enrollmentId}`);
      setClassrooms(prev => prev.filter(c => c.id !== enrollmentId));
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Siniftan ayrilirken hata olustu');
    }
  };

  const getSubjectIcon = (subject: string | null) => {
    switch (subject?.toLowerCase()) {
      case 'matematik':
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
        );
      case 'fizik':
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        );
      case 'kimya':
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
          </svg>
        );
      case 'biyoloji':
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
        );
      default:
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
        );
    }
  };

  const getSubjectColor = (subject: string | null) => {
    switch (subject?.toLowerCase()) {
      case 'matematik': return 'bg-blue-500/20 text-blue-400';
      case 'fizik': return 'bg-amber-500/20 text-amber-400';
      case 'kimya': return 'bg-emerald-500/20 text-emerald-400';
      case 'biyoloji': return 'bg-pink-500/20 text-pink-400';
      default: return 'bg-slate-500/20 text-slate-400';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">Siniflarim</h1>
            <p className="text-slate-400 mt-2">
              Kayitli oldugunuz siniflar
            </p>
          </div>
          <Link
            to="/sinifa-katil"
            className="mt-4 sm:mt-0 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            Sinifa Katil
          </Link>
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

        {/* Content */}
        {isLoading ? (
          <div className="flex justify-center py-16">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
        ) : classrooms.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-24 h-24 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-12 h-12 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-white mb-2">Henuz Bir Sinifa Kayitli Degilsiniz</h2>
            <p className="text-slate-400 mb-6">
              Ogretmeninizden aldiginiz katilim koduyla sinifa katilabilirsiniz
            </p>
            <Link
              to="/sinifa-katil"
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              Sinifa Katil
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {classrooms.map((classroom) => (
              <div
                key={classroom.id}
                className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl overflow-hidden hover:border-slate-600 transition-colors"
              >
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${getSubjectColor(classroom.subject)}`}>
                      {getSubjectIcon(classroom.subject)}
                    </div>
                    <span className={`px-2 py-1 rounded text-xs ${
                      classroom.status === 'active'
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : 'bg-slate-500/20 text-slate-400'
                    }`}>
                      {classroom.status === 'active' ? 'Aktif' : 'Pasif'}
                    </span>
                  </div>

                  <h3 className="text-lg font-semibold text-white mb-1">{classroom.classroom_name}</h3>
                  <p className="text-slate-400 text-sm mb-4">{classroom.teacher_name}</p>

                  <div className="flex flex-wrap gap-2 mb-4">
                    <span className="px-2 py-1 bg-slate-700 rounded text-xs text-slate-300">
                      {classroom.grade}. Sinif
                    </span>
                    {classroom.subject && (
                      <span className="px-2 py-1 bg-slate-700 rounded text-xs text-slate-300">
                        {classroom.subject}
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-slate-500 mb-4">
                    Katilim: {new Date(classroom.enrolled_at).toLocaleDateString('tr-TR')}
                  </p>

                  <div className="flex gap-2">
                    <Link
                      to={`/sohbet?classroom=${classroom.classroom_id}`}
                      className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors text-center"
                    >
                      Calisma Baslat
                    </Link>
                    <button
                      onClick={() => handleLeaveClassroom(classroom.id, classroom.classroom_name)}
                      className="px-3 py-2 bg-slate-700 hover:bg-red-500/20 hover:text-red-400 text-slate-400 rounded-lg transition-colors"
                      title="Siniftan Ayril"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default MyClassrooms;
