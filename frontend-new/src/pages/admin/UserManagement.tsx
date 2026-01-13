/**
 * User Management Page
 * List and manage all users in the platform
 */
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { AdminLayout } from '../../components/layout';
import api from '../../services/api';

interface UserItem {
  id: number;
  email: string;
  full_name: string;
  role: string;
  grade?: number;
  school_id?: number;
  school_name?: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

interface UserListResponse {
  items: UserItem[];
  total: number;
  page: number;
  page_size: number;
}

interface SchoolOption {
  id: number;
  name: string;
}

const UserManagement = () => {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [schools, setSchools] = useState<SchoolOption[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  // Filters
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [schoolFilter, setSchoolFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  useEffect(() => {
    fetchUsers();
  }, [page, roleFilter, schoolFilter, statusFilter]);

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

  const fetchUsers = async () => {
    try {
      setIsLoading(true);
      const params: any = { page, page_size: pageSize };
      if (search) params.search = search;
      if (roleFilter) params.role = roleFilter;
      if (schoolFilter) params.school_id = parseInt(schoolFilter);
      if (statusFilter) params.is_active = statusFilter === 'active';

      const response = await api.get<UserListResponse>('/admin/users', { params });
      setUsers(response.data.items);
      setTotal(response.data.total);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Kullanicilar yuklenirken hata olustu');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchUsers();
  };

  const handleToggleStatus = async (userId: number, currentStatus: boolean) => {
    try {
      await api.put(`/admin/users/${userId}`, { is_active: !currentStatus });
      fetchUsers();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Islem basarisiz');
    }
  };

  const handleDelete = async (userId: number, userName: string) => {
    if (!confirm(`"${userName}" kullanicisini silmek istediginize emin misiniz? Bu islem geri alinamaz.`)) return;

    try {
      await api.delete(`/admin/users/${userId}`);
      fetchUsers();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Silme islemi basarisiz');
    }
  };

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'platform_admin':
        return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
      case 'school_admin':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'teacher':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const getRoleLabel = (role: string) => {
    switch (role) {
      case 'platform_admin': return 'Platform Admin';
      case 'school_admin': return 'Okul Admin';
      case 'teacher': return 'Ogretmen';
      case 'student': return 'Ogrenci';
      default: return role;
    }
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <AdminLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">Kullanici Yonetimi</h1>
            <p className="text-slate-400 mt-2">
              Toplam {total} kullanici
            </p>
          </div>
          <Link
            to="/admin/kullanicilar/yeni"
            className="mt-4 sm:mt-0 px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            Yeni Kullanici
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
                placeholder="Isim veya email ara..."
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none"
              />
            </div>
            <select
              value={roleFilter}
              onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
              className="px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-purple-500 outline-none"
            >
              <option value="">Tum Roller</option>
              <option value="student">Ogrenci</option>
              <option value="teacher">Ogretmen</option>
              <option value="school_admin">Okul Admin</option>
              <option value="platform_admin">Platform Admin</option>
            </select>
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

        {/* Users Table */}
        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl overflow-hidden">
          {isLoading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
            </div>
          ) : users.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-slate-400">Kullanici bulunamadi</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-slate-400 text-sm border-b border-slate-700 bg-slate-800/50">
                    <th className="px-6 py-4 font-medium">Kullanici</th>
                    <th className="px-6 py-4 font-medium">Rol</th>
                    <th className="px-6 py-4 font-medium">Okul</th>
                    <th className="px-6 py-4 font-medium">Sinif</th>
                    <th className="px-6 py-4 font-medium">Durum</th>
                    <th className="px-6 py-4 font-medium">Islemler</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                  {users.map((user) => (
                    <tr key={user.id} className="hover:bg-slate-700/30 transition-colors">
                      <td className="px-6 py-4">
                        <div>
                          <p className="font-medium text-white">{user.full_name}</p>
                          <p className="text-sm text-slate-400">{user.email}</p>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded text-xs border ${getRoleBadge(user.role)}`}>
                          {getRoleLabel(user.role)}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-300">
                        {user.school_name || '-'}
                      </td>
                      <td className="px-6 py-4 text-slate-300">
                        {user.grade ? `${user.grade}. Sinif` : '-'}
                      </td>
                      <td className="px-6 py-4">
                        {user.is_active ? (
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
                            to={`/admin/kullanicilar/${user.id}`}
                            className="p-2 hover:bg-blue-500/20 rounded-lg transition-colors"
                            title="Detay"
                          >
                            <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                            </svg>
                          </Link>
                          {user.role !== 'platform_admin' && (
                            <>
                              <button
                                onClick={() => handleToggleStatus(user.id, user.is_active)}
                                className={`p-2 rounded-lg transition-colors ${
                                  user.is_active
                                    ? 'hover:bg-amber-500/20'
                                    : 'hover:bg-emerald-500/20'
                                }`}
                                title={user.is_active ? 'Devre Disi Birak' : 'Aktifles'}
                              >
                                {user.is_active ? (
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
                                onClick={() => handleDelete(user.id, user.full_name)}
                                className="p-2 hover:bg-red-500/20 rounded-lg transition-colors"
                                title="Sil"
                              >
                                <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                              </button>
                            </>
                          )}
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

export default UserManagement;
