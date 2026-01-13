/**
 * Create New School Page
 * Form for platform admins to create a new school
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AdminLayout } from '../../components/layout';
import type { TierInfo, School } from '../../types';
import api from '../../services/api';

interface SchoolFormData {
  name: string;
  slug: string;
  admin_email: string;
  phone: string;
  address: string;
  city: string;
  tier: string;
}

const SchoolCreate = () => {
  const navigate = useNavigate();
  const [tiers, setTiers] = useState<TierInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState<SchoolFormData>({
    name: '',
    slug: '',
    admin_email: '',
    phone: '',
    address: '',
    city: '',
    tier: 'small',
  });

  useEffect(() => {
    fetchTiers();
  }, []);

  const fetchTiers = async () => {
    try {
      const response = await api.get<TierInfo[]>('/admin/schools/tiers');
      setTiers(response.data);
    } catch (err) {
      console.error('Failed to fetch tiers', err);
    }
  };

  // Auto-generate slug from name
  const handleNameChange = (name: string) => {
    setFormData({
      ...formData,
      name,
      slug: name
        .toLowerCase()
        .replace(/[^a-z0-9\s-]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .trim(),
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!formData.name.trim()) {
      setError('Okul adi zorunludur');
      return;
    }
    if (!formData.slug.trim()) {
      setError('Slug zorunludur');
      return;
    }
    if (!formData.admin_email.trim()) {
      setError('Admin email zorunludur');
      return;
    }

    try {
      setIsLoading(true);
      const response = await api.post<School>('/admin/schools', formData);
      navigate(`/admin/okullar/${response.data.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Okul olusturulurken hata olustu');
    } finally {
      setIsLoading(false);
    }
  };

  const selectedTier = tiers.find(t => t.name === formData.tier);

  return (
    <AdminLayout>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/admin/okullar')}
            className="text-slate-400 hover:text-white flex items-center gap-2 mb-4"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Geri
          </button>
          <h1 className="text-3xl font-bold text-white">Yeni Okul Olustur</h1>
          <p className="text-slate-400 mt-2">
            Platform icin yeni bir okul hesabi olusturun
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Info */}
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Temel Bilgiler</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Okul Adi *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => handleNameChange(e.target.value)}
                  placeholder="ornegin: Yediiklim Anadolu Lisesi"
                  className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Slug (URL) *
                </label>
                <div className="flex items-center">
                  <span className="px-4 py-3 bg-slate-600 border border-r-0 border-slate-600 rounded-l-lg text-slate-400">
                    /okul/
                  </span>
                  <input
                    type="text"
                    value={formData.slug}
                    onChange={(e) => setFormData({ ...formData, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '') })}
                    placeholder="yediiklim-anadolu"
                    className="flex-1 px-4 py-3 bg-slate-700 border border-slate-600 rounded-r-lg text-white placeholder-slate-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                    required
                  />
                </div>
                <p className="text-xs text-slate-500 mt-1">Sadece kucuk harf, rakam ve tire kullanin</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Admin Email *
                </label>
                <input
                  type="email"
                  value={formData.admin_email}
                  onChange={(e) => setFormData({ ...formData, admin_email: e.target.value })}
                  placeholder="admin@okul.edu.tr"
                  className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                  required
                />
                <p className="text-xs text-slate-500 mt-1">Okul yoneticisinin email adresi</p>
              </div>
            </div>
          </div>

          {/* Contact Info */}
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Iletisim Bilgileri</h2>

            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Telefon
                  </label>
                  <input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    placeholder="0212 555 1234"
                    className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Sehir
                  </label>
                  <input
                    type="text"
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    placeholder="Istanbul"
                    className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Adres
                </label>
                <textarea
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  placeholder="Tam adres..."
                  rows={3}
                  className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none"
                />
              </div>
            </div>
          </div>

          {/* Tier Selection */}
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Abonelik Paketi</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {tiers.map((tier) => (
                <button
                  key={tier.name}
                  type="button"
                  onClick={() => setFormData({ ...formData, tier: tier.name })}
                  className={`p-4 rounded-xl border-2 text-left transition-all ${
                    formData.tier === tier.name
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-slate-600 hover:border-slate-500'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-white capitalize">{tier.name}</h3>
                    {formData.tier === tier.name && (
                      <svg className="w-5 h-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>
                  <p className="text-2xl font-bold text-white mb-2">
                    {tier.price_try.toLocaleString('tr-TR')} <span className="text-sm font-normal text-slate-400">TL/ay</span>
                  </p>
                  <ul className="space-y-1 text-sm text-slate-400">
                    <li>{tier.max_students} ogrenci</li>
                    <li>{tier.max_teachers} ogretmen</li>
                    <li>{tier.max_classrooms} sinif</li>
                  </ul>
                </button>
              ))}
            </div>
          </div>

          {/* Summary */}
          {selectedTier && (
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-2">Ozet</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-slate-400">Okul Adi</p>
                  <p className="text-white font-medium">{formData.name || '-'}</p>
                </div>
                <div>
                  <p className="text-slate-400">Paket</p>
                  <p className="text-white font-medium capitalize">{selectedTier.name}</p>
                </div>
                <div>
                  <p className="text-slate-400">Aylik Ucret</p>
                  <p className="text-white font-medium">{selectedTier.price_try.toLocaleString('tr-TR')} TL</p>
                </div>
                <div>
                  <p className="text-slate-400">Limitler</p>
                  <p className="text-white font-medium">
                    {selectedTier.max_students} ogrenci, {selectedTier.max_teachers} ogretmen
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Submit */}
          <div className="flex gap-4">
            <button
              type="button"
              onClick={() => navigate('/admin/okullar')}
              className="flex-1 px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium transition-colors"
            >
              Iptal
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
            >
              {isLoading ? 'Olusturuluyor...' : 'Okul Olustur'}
            </button>
          </div>
        </form>
      </div>
    </AdminLayout>
  );
};

export default SchoolCreate;
