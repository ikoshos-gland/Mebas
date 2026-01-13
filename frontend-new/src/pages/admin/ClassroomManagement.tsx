/**
 * Classroom Management Page
 * List and manage all classrooms in the platform
 */
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { AdminLayout } from '../../components/layout';
import api from '../../services/api';

interface ClassroomItem {
  id: number;
  name: string;
  join_code: string;
  school_id: number;
  school_name?: string;
  teacher_id: number;
  teacher_name?: string;
  grade: number;
  subject?: string;
  student_count: number;
  is_active: boolean;
  created_at: string;
}

interface ClassroomListResponse {
  items: ClassroomItem[];
  total: number;
  page: number;
  page_size: number;
}

interface SchoolOption {
  id: number;
  name: string;
}

const ClassroomManagement = () => {
  const [classrooms, setClassrooms] = useState<ClassroomItem[]>([]);
  const [schools, setSchools] = useState<SchoolOption[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  // Filters
  const [search, setSearch] = useState('');
  const [schoolFilter, setSchoolFilter] = useState<string>('');
  const [gradeFilter, setGradeFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  useEffect(() => {
    fetchClassrooms();
  }, [page, schoolFilter, gradeFilter, statusFilter]);

  useEffect(() => {
    fetchSchools();
  }, []);

  const fetchSchools = async () => {
    try {
      const response = await api.get('/admin/schools');
      setSchools(response.data.items.map((s: any) => ({ id: s.id, name: s.name })));
    } catch (err) {
      console.error('Failed to fetch schools', err);
    }
  };

  const fetchClassrooms = async () => {
    try {
      setIsLoading(true);
      const params: any = { page, page_size: pageSize };
      if (search) params.search = search;
      if (schoolFilter) params.school_id = parseInt(schoolFilter);
      if (gradeFilter) params.grade = parseInt(gradeFilter);
      if (statusFilter) params.is_active = statusFilter === 'active';

      const response = await api.get<ClassroomListResponse>('/admin/classrooms', { params });
      setClassrooms(response.data.items);
      setTotal(response.data.total);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Siniflar yuklenirken hata olustu');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchClassrooms();
  };

  const handleToggleStatus = async (classroomId: number, currentStatus: boolean) => {
    try {
      await api.put(`/admin/classrooms/${classroomId}`, { is_active: !currentStatus });
      fetchClassrooms();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Islem basarisiz');
    }
  };

  const handleDelete = async (classroomId: number, classroomName: string) => {
    if (!confirm(`"${classroomName}" sinifini silmek istediginize emin misiniz? Tum ogrenci kayitlari da silinecektir.`)) return;

    try {
      await api.delete(`/admin/classrooms/${classroomId}`);
      fetchClassrooms();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Silme islemi basarisiz');
    }
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <AdminLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">Sinif Yonetimi</h1>
            <p className="text-slate-400 mt-2">
              Toplam {total} sinif
            </p>
          </div>
          <Link
            to="/admin/siniflar/yeni"
            className="mt-4 sm:mt-0 px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            Yeni Sinif
          </Link>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
            {error}
            <button onClick={() => setError(null)} className="ml-4 text-red-300 hover:text-red-200">
              Kapat
            </button>
          </div>
        )}

        {/* Filters */}
        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-4 mb-6">
          <form onSubmit={handleSearch} className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Sinif adi veya katilim kodu ara..."
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none"
              />
            </div>
            <select
              value={schoolFilter}
              onChange={(e) => { setSchoolFilter(e.target.value); setPage(1); }}
              className="px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-purple-500 outline-none"
            >
              <option value="">Tum Okullar</option>
              {schools.map((school) => (
                <option key={school.id} value={school.id}>{school.name}</option>
              ))}
            </select>
            <select
              value={gradeFilter}
              onChange={(e) => { setGradeFilter(e.target.value); setPage(1); }}
              className="px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-purple-500 outline-none"
            >
              <option value="">Tum Seviyeler</option>
              {[...Array(12)].map((_, i) => (
                <option key={i + 1} value={i + 1}>{i + 1}. Sinif</option>
              ))}
            </select>
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className="px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-purple-500 outline-none"
            >
              <option value="">Tum Durumlar</option>
              <option value="active">Aktif</option>
              <option value="inactive">Pasif</option>
            </select>
            <button
              type="submit"
              className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors"
            >
              Ara
            </button>
          </form>
        </div>

        {/* Classrooms Table */}
        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl overflow-hidden">
          {isLoading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
            </div>
          ) : classrooms.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-slate-400">Sinif bulunamadi</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-slate-400 text-sm border-b border-slate-700 bg-slate-800/50">
                    <th className="px-6 py-4 font-medium">Sinif</th>
                    <th className="px-6 py-4 font-medium">Okul</th>
                    <th className="px-6 py-4 font-medium">Ogretmen</th>
                    <th className="px-6 py-4 font-medium">Seviye</th>
                    <th className="px-6 py-4 font-medium">Ogrenci</th>
                    <th className="px-6 py-4 font-medium">Durum</th>
                    <th className="px-6 py-4 font-medium">Islemler</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                  {classrooms.map((classroom) => (
                    <tr key={classroom.id} className="hover:bg-slate-700/30 transition-colors">
                      <td className="px-6 py-4">
                        <div>
                          <p className="font-medium text-white">{classroom.name}</p>
                          <p className="text-sm text-slate-400 font-mono">{classroom.join_code}</p>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-slate-300">
                        {classroom.school_name || '-'}
                      </td>
                      <td className="px-6 py-4 text-slate-300">
                        {classroom.teacher_name || '-'}
                      </td>
                      <td className="px-6 py-4 text-slate-300">
                        {classroom.grade}. Sinif
                        {classroom.subject && (
                          <span className="text-slate-500 text-sm block">{classroom.subject}</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-sm">
                          {classroom.student_count} ogrenci
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        {classroom.is_active ? (
                          <span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 rounded text-xs">
                            Aktif
                          </span>
                        ) : (
                          <span className="px-2 py-1 bg-red-500/20 text-red-400 rounded text-xs">
                            Pasif
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <Link
                            to={`/admin/siniflar/${classroom.id}`}
                            className="p-2 hover:bg-blue-500/20 rounded-lg transition-colors"
                            title="Detay"
                          >
                            <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                            </svg>
                          </Link>
                          <button
                            onClick={() => handleToggleStatus(classroom.id, classroom.is_active)}
                            className={`p-2 rounded-lg transition-colors ${
                              classroom.is_active
                                ? 'hover:bg-amber-500/20'
                                : 'hover:bg-emerald-500/20'
                            }`}
                            title={classroom.is_active ? 'Devre Disi Birak' : 'Aktifles'}
                          >
                            {classroom.is_active ? (
                              <svg className="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                              </svg>
                            ) : (
                              <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                            )}
                          </button>
                          <button
                            onClick={() => handleDelete(classroom.id, classroom.name)}
                            className="p-2 hover:bg-red-500/20 rounded-lg transition-colors"
                            title="Sil"
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

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-6 py-4 border-t border-slate-700 flex items-center justify-between">
              <p className="text-sm text-slate-400">
                Sayfa {page} / {totalPages}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-4 py-2 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm transition-colors"
                >
                  Onceki
                </button>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-4 py-2 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm transition-colors"
                >
                  Sonraki
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </AdminLayout>
  );
};

export default ClassroomManagement;
