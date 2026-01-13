/**
 * User Detail Page
 * View and edit user information
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AdminLayout } from '../../components/layout';
import api from '../../services/api';

interface UserDetail {
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
  firebase_uid: string;
  classroom_count?: number;
  conversation_count?: number;
}

interface SchoolOption {
  id: number;
  name: string;
}

const UserDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [user, setUser] = useState<UserDetail | null>(null);
  const [schools, setSchools] = useState<SchoolOption[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [editData, setEditData] = useState({
    full_name: '',
    role: '',
    grade: '',
    school_id: '',
  });

  useEffect(() => {
    fetchUser();
    fetchSchools();
  }, [id]);

  const fetchUser = async () => {
    try {
      setIsLoading(true);
      const response = await api.get<UserDetail>(`/admin/users/${id}`);
      setUser(response.data);
      setEditData({
        full_name: response.data.full_name,
        role: response.data.role,
        grade: response.data.grade?.toString() || '',
        school_id: response.data.school_id?.toString() || '',
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Kullanici yuklenirken hata olustu');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchSchools = async () => {
    try {
      const response = await api.get('/admin/schools');
      setSchools(response.data.items.map((s: any) => ({ id: s.id, name: s.name })));
    } catch (err) {
      console.error('Failed to fetch schools', err);
    }
  };

  const handleSave = async () => {
    if (!user) return;

    try {
      setIsSaving(true);
      setError(null);

      const payload: any = {
        full_name: editData.full_name,
        role: editData.role,
      };

      if (editData.role === 'student' && editData.grade) {
        payload.grade = parseInt(editData.grade);
      } else {
        payload.grade = null;
      }

      if (editData.school_id) {
        payload.school_id = parseInt(editData.school_id);
      } else {
        payload.school_id = null;
      }

      await api.put(`/admin/users/${id}`, payload);
      setSuccessMessage('Kullanici basariyla guncellendi');
      setIsEditing(false);
      fetchUser();

      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Guncelleme basarisiz');
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggleStatus = async () => {
    if (!user) return;

    try {
      await api.put(`/admin/users/${id}`, { is_active: !user.is_active });
      setSuccessMessage(user.is_active ? 'Kullanici devre disi birakildi' : 'Kullanici aktif edildi');
      fetchUser();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Islem basarisiz');
    }
  };

  const handleResetPassword = async () => {
    if (!user) return;

    try {
      const response = await api.post(`/admin/users/${id}/reset-password`);
      setSuccessMessage('Sifre sifirlama linki olusturuldu. Link: ' + response.data.reset_link?.substring(0, 50) + '...');
      setTimeout(() => setSuccessMessage(null), 10000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Sifre sifirlama basarisiz');
    }
  };

  const handleDelete = async () => {
    if (!user) return;
    if (!confirm(`"${user.full_name}" kullanicisini silmek istediginize emin misiniz? Bu islem geri alinamaz.`)) return;

    try {
      await api.delete(`/admin/users/${id}`);
      navigate('/admin/kullanicilar');
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

  if (isLoading) {
    return (
      <AdminLayout>
        <div className="flex justify-center items-center min-h-[60vh]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
        </div>
      </AdminLayout>
    );
  }

  if (!user) {
    return (
      <AdminLayout>
        <div className="max-w-3xl mx-auto px-4 py-8">
          <div className="text-center py-12">
            <p className="text-slate-400">Kullanici bulunamadi</p>
            <button
              onClick={() => navigate('/admin/kullanicilar')}
              className="mt-4 px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg"
            >
              Geri Don
            </button>
          </div>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/admin/kullanicilar')}
            className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors mb-4"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Kullanicilara Don
          </button>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white">{user.full_name}</h1>
              <p className="text-slate-400 mt-1">{user.email}</p>
            </div>
            <span className={`px-3 py-1 rounded text-sm border ${getRoleBadge(user.role)}`}>
              {getRoleLabel(user.role)}
            </span>
          </div>
        </div>

        {/* Messages */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 flex justify-between items-center">
            {error}
            <button onClick={() => setError(null)} className="text-red-300 hover:text-red-200">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {successMessage && (
          <div className="mb-6 p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400">
            {successMessage}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Info */}
          <div className="lg:col-span-2 space-y-6">
            {/* User Info Card */}
            <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-semibold text-white">Kullanici Bilgileri</h2>
                {user.role !== 'platform_admin' && (
                  <button
                    onClick={() => setIsEditing(!isEditing)}
                    className="px-4 py-2 text-sm bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
                  >
                    {isEditing ? 'Iptal' : 'Duzenle'}
                  </button>
                )}
              </div>

              {isEditing ? (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Isim Soyisim
                    </label>
                    <input
                      type="text"
                      value={editData.full_name}
                      onChange={(e) => setEditData(prev => ({ ...prev, full_name: e.target.value }))}
                      className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-purple-500 outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Rol
                    </label>
                    <select
                      value={editData.role}
                      onChange={(e) => setEditData(prev => ({ ...prev, role: e.target.value, grade: e.target.value !== 'student' ? '' : prev.grade }))}
                      className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-purple-500 outline-none"
                    >
                      <option value="student">Ogrenci</option>
                      <option value="teacher">Ogretmen</option>
                      <option value="school_admin">Okul Admin</option>
                    </select>
                  </div>

                  {editData.role === 'student' && (
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        Sinif Seviyesi
                      </label>
                      <select
                        value={editData.grade}
                        onChange={(e) => setEditData(prev => ({ ...prev, grade: e.target.value }))}
                        className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-purple-500 outline-none"
                      >
                        <option value="">Sinif secin</option>
                        {[...Array(12)].map((_, i) => (
                          <option key={i + 1} value={i + 1}>{i + 1}. Sinif</option>
                        ))}
                      </select>
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Okul
                    </label>
                    <select
                      value={editData.school_id}
                      onChange={(e) => setEditData(prev => ({ ...prev, school_id: e.target.value }))}
                      className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-purple-500 outline-none"
                    >
                      <option value="">Okul secin</option>
                      {schools.map((school) => (
                        <option key={school.id} value={school.id}>{school.name}</option>
                      ))}
                    </select>
                  </div>

                  <button
                    onClick={handleSave}
                    disabled={isSaving}
                    className="w-full px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-600/50 text-white rounded-lg font-medium transition-colors"
                  >
                    {isSaving ? 'Kaydediliyor...' : 'Degisiklikleri Kaydet'}
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex justify-between py-3 border-b border-slate-700">
                    <span className="text-slate-400">Email</span>
                    <span className="text-white">{user.email}</span>
                  </div>
                  <div className="flex justify-between py-3 border-b border-slate-700">
                    <span className="text-slate-400">Isim</span>
                    <span className="text-white">{user.full_name}</span>
                  </div>
                  <div className="flex justify-between py-3 border-b border-slate-700">
                    <span className="text-slate-400">Rol</span>
                    <span className="text-white">{getRoleLabel(user.role)}</span>
                  </div>
                  {user.grade && (
                    <div className="flex justify-between py-3 border-b border-slate-700">
                      <span className="text-slate-400">Sinif</span>
                      <span className="text-white">{user.grade}. Sinif</span>
                    </div>
                  )}
                  <div className="flex justify-between py-3 border-b border-slate-700">
                    <span className="text-slate-400">Okul</span>
                    <span className="text-white">{user.school_name || 'Atanmadi'}</span>
                  </div>
                  <div className="flex justify-between py-3 border-b border-slate-700">
                    <span className="text-slate-400">Kayit Tarihi</span>
                    <span className="text-white">
                      {new Date(user.created_at).toLocaleDateString('tr-TR')}
                    </span>
                  </div>
                  <div className="flex justify-between py-3">
                    <span className="text-slate-400">Firebase UID</span>
                    <span className="text-white font-mono text-sm">{user.firebase_uid?.substring(0, 20)}...</span>
                  </div>
                </div>
              )}
            </div>

            {/* Activity Stats */}
            <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
              <h2 className="text-lg font-semibold text-white mb-4">Aktivite</h2>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-700/50 rounded-lg p-4 text-center">
                  <p className="text-3xl font-bold text-purple-400">{user.classroom_count || 0}</p>
                  <p className="text-sm text-slate-400 mt-1">Sinif</p>
                </div>
                <div className="bg-slate-700/50 rounded-lg p-4 text-center">
                  <p className="text-3xl font-bold text-blue-400">{user.conversation_count || 0}</p>
                  <p className="text-sm text-slate-400 mt-1">Konusma</p>
                </div>
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Status Card */}
            <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
              <h2 className="text-lg font-semibold text-white mb-4">Durum</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Hesap Durumu</span>
                  {user.is_active ? (
                    <span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 rounded text-sm">
                      Aktif
                    </span>
                  ) : (
                    <span className="px-2 py-1 bg-red-500/20 text-red-400 rounded text-sm">
                      Pasif
                    </span>
                  )}
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Email Dogrulama</span>
                  {user.is_verified ? (
                    <span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 rounded text-sm">
                      Dogrulandi
                    </span>
                  ) : (
                    <span className="px-2 py-1 bg-amber-500/20 text-amber-400 rounded text-sm">
                      Bekliyor
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Actions Card */}
            {user.role !== 'platform_admin' && (
              <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
                <h2 className="text-lg font-semibold text-white mb-4">Islemler</h2>
                <div className="space-y-3">
                  <button
                    onClick={handleToggleStatus}
                    className={`w-full px-4 py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
                      user.is_active
                        ? 'bg-amber-500/20 hover:bg-amber-500/30 text-amber-400'
                        : 'bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400'
                    }`}
                  >
                    {user.is_active ? (
                      <>
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                        </svg>
                        Devre Disi Birak
                      </>
                    ) : (
                      <>
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Aktif Et
                      </>
                    )}
                  </button>

                  <button
                    onClick={handleResetPassword}
                    className="w-full px-4 py-3 bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                    </svg>
                    Sifre Sifirla
                  </button>

                  <button
                    onClick={handleDelete}
                    className="w-full px-4 py-3 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                    Kullaniciyi Sil
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </AdminLayout>
  );
};

export default UserDetailPage;
