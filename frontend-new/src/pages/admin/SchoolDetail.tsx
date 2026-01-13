/**
 * School Detail & Edit Page
 * View and edit school information
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { AdminLayout } from '../../components/layout';
import type { SchoolWithStats, TierInfo } from '../../types';
import api from '../../services/api';

interface SchoolUser {
  id: number;
  email: string;
  full_name: string;
  role: string;
  grade?: number;
  is_active: boolean;
  created_at: string;
  last_login?: string;
}

const SchoolDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [school, setSchool] = useState<SchoolWithStats | null>(null);
  const [users, setUsers] = useState<SchoolUser[]>([]);
  const [tiers, setTiers] = useState<TierInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Edit mode
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [editForm, setEditForm] = useState({
    name: '',
    admin_email: '',
    phone: '',
    address: '',
    city: '',
  });

  // Tab state
  const [activeTab, setActiveTab] = useState<'info' | 'users' | 'tier'>('info');

  useEffect(() => {
    fetchSchool();
    fetchTiers();
  }, [id]);

  const fetchSchool = async () => {
    try {
      setIsLoading(true);
      const response = await api.get<SchoolWithStats>(`/admin/schools/${id}`);
      setSchool(response.data);
      setEditForm({
        name: response.data.name,
        admin_email: response.data.admin_email,
        phone: response.data.phone || '',
        address: response.data.address || '',
        city: response.data.city || '',
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Okul yuklenirken hata olustu');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchUsers = async () => {
    try {
      const response = await api.get(`/admin/schools/${id}/users`, {
        params: { page_size: 100 }
      });
      setUsers(response.data.items);
    } catch (err) {
      console.error('Failed to fetch users', err);
    }
  };

  const fetchTiers = async () => {
    try {
      const response = await api.get<TierInfo[]>('/admin/schools/tiers');
      setTiers(response.data);
    } catch (err) {
      console.error('Failed to fetch tiers', err);
    }
  };

  useEffect(() => {
    if (activeTab === 'users' && users.length === 0) {
      fetchUsers();
    }
  }, [activeTab]);

  const handleSave = async () => {
    if (!school) return;

    try {
      setIsSaving(true);
      setError(null);

      await api.put(`/admin/schools/${id}`, editForm);

      setSuccessMessage('Okul bilgileri guncellendi');
      setIsEditing(false);
      fetchSchool();

      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Guncelleme basarisiz');
    } finally {
      setIsSaving(false);
    }
  };

  const handleTierChange = async (newTier: string) => {
    if (!school || school.tier === newTier) return;

    if (!confirm(`Tier'i ${newTier} olarak degistirmek istediginize emin misiniz?`)) return;

    try {
      setError(null);
      await api.put(`/admin/schools/${id}/tier`, { tier: newTier });
      setSuccessMessage('Tier guncellendi');
      fetchSchool();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Tier guncellenemedi');
    }
  };

  const handleToggleStatus = async () => {
    if (!school) return;

    const action = school.is_active ? 'deactivate' : 'activate';
    const message = school.is_active
      ? 'Bu okulu devre disi birakmak istediginize emin misiniz?'
      : 'Bu okulu aktif etmek istediginize emin misiniz?';

    if (!confirm(message)) return;

    try {
      await api.post(`/admin/schools/${id}/${action}`);
      setSuccessMessage(school.is_active ? 'Okul devre disi birakildi' : 'Okul aktif edildi');
      fetchSchool();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Islem basarisiz');
    }
  };

  const handleRoleChange = async (userId: number, newRole: string) => {
    try {
      await api.put(`/admin/schools/${id}/users/${userId}/role?role=${newRole}`);
      setSuccessMessage('Kullanici rolu guncellendi');
      fetchUsers();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Rol guncellenemedi');
    }
  };

  const handleRemoveUser = async (userId: number, userName: string) => {
    if (!confirm(`${userName} kullanicisini okuldan cikarmak istediginize emin misiniz?`)) return;

    try {
      await api.delete(`/admin/schools/${id}/users/${userId}`);
      setSuccessMessage('Kullanici okuldan cikarildi');
      fetchUsers();
      fetchSchool();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Islem basarisiz');
    }
  };

  const getTierBadgeColor = (tier: string) => {
    switch (tier) {
      case 'large': return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
      case 'medium': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  if (isLoading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      </AdminLayout>
    );
  }

  if (!school) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center">
            <p className="text-slate-400 mb-4">Okul bulunamadi</p>
            <Link to="/admin/okullar" className="text-blue-400 hover:text-blue-300">
              Okul listesine don
            </Link>
          </div>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/admin/okullar')}
            className="text-slate-400 hover:text-white flex items-center gap-2 mb-4"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Okul Listesi
          </button>

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-3xl font-bold text-white">{school.name}</h1>
                <span className={`px-3 py-1 rounded-full text-xs border ${getTierBadgeColor(school.tier)}`}>
                  {school.tier}
                </span>
                {school.is_active ? (
                  <span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 rounded text-xs">
                    Aktif
                  </span>
                ) : (
                  <span className="px-2 py-1 bg-red-500/20 text-red-400 rounded text-xs">
                    Pasif
                  </span>
                )}
              </div>
              <p className="text-slate-400 mt-1">{school.slug}</p>
            </div>

            <div className="flex gap-2">
              <button
                onClick={handleToggleStatus}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  school.is_active
                    ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                    : 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30'
                }`}
              >
                {school.is_active ? 'Devre Disi Birak' : 'Aktif Et'}
              </button>
            </div>
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

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
            <p className="text-slate-400 text-sm">Ogrenci</p>
            <p className="text-2xl font-bold text-white">
              {school.student_count} <span className="text-sm text-slate-500">/ {school.max_students}</span>
            </p>
          </div>
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
            <p className="text-slate-400 text-sm">Ogretmen</p>
            <p className="text-2xl font-bold text-white">
              {school.teacher_count} <span className="text-sm text-slate-500">/ {school.max_teachers}</span>
            </p>
          </div>
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
            <p className="text-slate-400 text-sm">Sinif</p>
            <p className="text-2xl font-bold text-white">{school.classroom_count}</p>
          </div>
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
            <p className="text-slate-400 text-sm">Olusturulma</p>
            <p className="text-lg font-medium text-white">
              {new Date(school.created_at).toLocaleDateString('tr-TR')}
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-slate-700 mb-6">
          <nav className="flex gap-6">
            {[
              { id: 'info', label: 'Okul Bilgileri' },
              { id: 'users', label: 'Kullanicilar' },
              { id: 'tier', label: 'Abonelik' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`pb-4 text-sm font-medium transition-colors border-b-2 -mb-[1px] ${
                  activeTab === tab.id
                    ? 'text-blue-400 border-blue-400'
                    : 'text-slate-400 border-transparent hover:text-white'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'info' && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-semibold text-white">Okul Bilgileri</h2>
              {!isEditing ? (
                <button
                  onClick={() => setIsEditing(true)}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
                >
                  Duzenle
                </button>
              ) : (
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setIsEditing(false);
                      setEditForm({
                        name: school.name,
                        admin_email: school.admin_email,
                        phone: school.phone || '',
                        address: school.address || '',
                        city: school.city || '',
                      });
                    }}
                    className="px-4 py-2 bg-slate-600 hover:bg-slate-500 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    Iptal
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={isSaving}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-600/50 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    {isSaving ? 'Kaydediliyor...' : 'Kaydet'}
                  </button>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm text-slate-400 mb-2">Okul Adi</label>
                {isEditing ? (
                  <input
                    type="text"
                    value={editForm.name}
                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-blue-500 outline-none"
                  />
                ) : (
                  <p className="text-white font-medium">{school.name}</p>
                )}
              </div>

              <div>
                <label className="block text-sm text-slate-400 mb-2">Admin Email</label>
                {isEditing ? (
                  <input
                    type="email"
                    value={editForm.admin_email}
                    onChange={(e) => setEditForm({ ...editForm, admin_email: e.target.value })}
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-blue-500 outline-none"
                  />
                ) : (
                  <p className="text-white">{school.admin_email}</p>
                )}
              </div>

              <div>
                <label className="block text-sm text-slate-400 mb-2">Telefon</label>
                {isEditing ? (
                  <input
                    type="tel"
                    value={editForm.phone}
                    onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-blue-500 outline-none"
                    placeholder="-"
                  />
                ) : (
                  <p className="text-white">{school.phone || '-'}</p>
                )}
              </div>

              <div>
                <label className="block text-sm text-slate-400 mb-2">Sehir</label>
                {isEditing ? (
                  <input
                    type="text"
                    value={editForm.city}
                    onChange={(e) => setEditForm({ ...editForm, city: e.target.value })}
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-blue-500 outline-none"
                    placeholder="-"
                  />
                ) : (
                  <p className="text-white">{school.city || '-'}</p>
                )}
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm text-slate-400 mb-2">Adres</label>
                {isEditing ? (
                  <textarea
                    value={editForm.address}
                    onChange={(e) => setEditForm({ ...editForm, address: e.target.value })}
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-blue-500 outline-none resize-none"
                    rows={2}
                    placeholder="-"
                  />
                ) : (
                  <p className="text-white">{school.address || '-'}</p>
                )}
              </div>

              <div>
                <label className="block text-sm text-slate-400 mb-2">Slug</label>
                <p className="text-slate-500">{school.slug}</p>
                <p className="text-xs text-slate-600 mt-1">Slug degistirilemez</p>
              </div>

              <div>
                <label className="block text-sm text-slate-400 mb-2">Son Guncelleme</label>
                <p className="text-white">
                  {new Date(school.updated_at).toLocaleString('tr-TR')}
                </p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'users' && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
            <div className="p-4 border-b border-slate-700">
              <h2 className="text-lg font-semibold text-white">Kullanicilar ({users.length})</h2>
            </div>

            {users.length === 0 ? (
              <div className="p-8 text-center text-slate-400">
                Bu okulda henuz kullanici yok
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-slate-400 text-sm border-b border-slate-700 bg-slate-800/50">
                      <th className="px-4 py-3 font-medium">Kullanici</th>
                      <th className="px-4 py-3 font-medium">Rol</th>
                      <th className="px-4 py-3 font-medium">Durum</th>
                      <th className="px-4 py-3 font-medium">Son Giris</th>
                      <th className="px-4 py-3 font-medium">Islemler</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700">
                    {users.map((user) => (
                      <tr key={user.id} className="text-slate-300 hover:bg-slate-700/30">
                        <td className="px-4 py-3">
                          <p className="font-medium text-white">{user.full_name}</p>
                          <p className="text-sm text-slate-400">{user.email}</p>
                        </td>
                        <td className="px-4 py-3">
                          <select
                            value={user.role}
                            onChange={(e) => handleRoleChange(user.id, e.target.value)}
                            className="bg-slate-700 border border-slate-600 rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-blue-500"
                          >
                            <option value="student">Ogrenci</option>
                            <option value="teacher">Ogretmen</option>
                            <option value="school_admin">Okul Admin</option>
                          </select>
                        </td>
                        <td className="px-4 py-3">
                          {user.is_active ? (
                            <span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 rounded text-xs">Aktif</span>
                          ) : (
                            <span className="px-2 py-1 bg-red-500/20 text-red-400 rounded text-xs">Pasif</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {user.last_login
                            ? new Date(user.last_login).toLocaleDateString('tr-TR')
                            : '-'
                          }
                        </td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => handleRemoveUser(user.id, user.full_name)}
                            className="p-1.5 hover:bg-red-500/20 rounded text-red-400 transition-colors"
                            title="Okuldan Cikar"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'tier' && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-6">Abonelik Paketi</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {tiers.map((tier) => (
                <button
                  key={tier.name}
                  onClick={() => handleTierChange(tier.name)}
                  className={`p-4 rounded-xl border-2 text-left transition-all ${
                    school.tier === tier.name
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-slate-600 hover:border-slate-500'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-white capitalize">{tier.name}</h3>
                    {school.tier === tier.name && (
                      <svg className="w-5 h-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>
                  <p className="text-2xl font-bold text-white mb-2">
                    {tier.price_try.toLocaleString('tr-TR')} <span className="text-sm font-normal text-slate-400">TL/ay</span>
                  </p>
                  <ul className="space-y-1 text-sm text-slate-400">
                    <li>Max {tier.max_students} ogrenci</li>
                    <li>Max {tier.max_teachers} ogretmen</li>
                    <li>Max {tier.max_classrooms} sinif</li>
                  </ul>
                </button>
              ))}
            </div>

            <div className="mt-6 p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
              <p className="text-amber-400 text-sm">
                <strong>Not:</strong> Tier degisikligi aninda uygulanir. Downgrade yaparken mevcut kullanici sayisi yeni limitin altinda olmalidir.
              </p>
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
};

export default SchoolDetail;
