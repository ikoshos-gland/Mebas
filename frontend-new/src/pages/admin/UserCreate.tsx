/**
 * Create New User Page
 * Form for platform admins to create a new user
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AdminLayout } from '../../components/layout';
import api from '../../services/api';

interface SchoolOption {
  id: number;
  name: string;
}

interface UserFormData {
  email: string;
  full_name: string;
  password: string;
  confirmPassword: string;
  role: string;
  grade: string;
  school_id: string;
}

const UserCreate = () => {
  const navigate = useNavigate();
  const [schools, setSchools] = useState<SchoolOption[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState<UserFormData>({
    email: '',
    full_name: '',
    password: '',
    confirmPassword: '',
    role: 'student',
    grade: '',
    school_id: '',
  });

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

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));

    // Role değiştiğinde grade'i temizle
    if (name === 'role' && value !== 'student') {
      setFormData(prev => ({ ...prev, [name]: value, grade: '' }));
    }
  };

  const validateForm = (): string | null => {
    if (!formData.email) return 'Email zorunludur';
    if (!formData.full_name) return 'Isim soyisim zorunludur';
    if (!formData.password) return 'Sifre zorunludur';
    if (formData.password.length < 6) return 'Sifre en az 6 karakter olmalidir';
    if (formData.password !== formData.confirmPassword) return 'Sifreler eslesmemektedir';
    if (formData.role === 'student' && !formData.grade) return 'Ogrenciler icin sinif seviyesi zorunludur';
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      const payload: any = {
        email: formData.email,
        full_name: formData.full_name,
        password: formData.password,
        role: formData.role,
      };

      if (formData.role === 'student' && formData.grade) {
        payload.grade = parseInt(formData.grade);
      }

      if (formData.school_id) {
        payload.school_id = parseInt(formData.school_id);
      }

      await api.post('/admin/users', payload);
      navigate('/admin/kullanicilar');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Kullanici olusturulurken hata olustu');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AdminLayout>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/admin/kullanicilar')}
            className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors mb-4"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Geri
          </button>
          <h1 className="text-3xl font-bold text-white">Yeni Kullanici Olustur</h1>
          <p className="text-slate-400 mt-2">
            Sisteme yeni bir kullanici ekleyin
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Temel Bilgiler */}
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Temel Bilgiler</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Email Adresi *
                </label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none"
                  placeholder="ornek@email.com"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Isim Soyisim *
                </label>
                <input
                  type="text"
                  name="full_name"
                  value={formData.full_name}
                  onChange={handleChange}
                  className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none"
                  placeholder="Ad Soyad"
                  required
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Sifre *
                  </label>
                  <input
                    type="password"
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none"
                    placeholder="En az 6 karakter"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Sifre Tekrar *
                  </label>
                  <input
                    type="password"
                    name="confirmPassword"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none"
                    placeholder="Sifrenizi tekrar girin"
                    required
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Rol ve Okul */}
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Rol ve Okul</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Kullanici Rolu *
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {[
                    { value: 'student', label: 'Ogrenci', icon: '🎓', color: 'slate' },
                    { value: 'teacher', label: 'Ogretmen', icon: '👨‍🏫', color: 'emerald' },
                    { value: 'school_admin', label: 'Okul Admin', icon: '🏫', color: 'blue' },
                  ].map((role) => (
                    <button
                      key={role.value}
                      type="button"
                      onClick={() => setFormData(prev => ({ ...prev, role: role.value, grade: role.value !== 'student' ? '' : prev.grade }))}
                      className={`
                        p-4 rounded-lg border-2 transition-all text-left
                        ${formData.role === role.value
                          ? `border-${role.color}-500 bg-${role.color}-500/10`
                          : 'border-slate-600 hover:border-slate-500'
                        }
                      `}
                    >
                      <span className="text-2xl mb-2 block">{role.icon}</span>
                      <span className={`font-medium ${formData.role === role.value ? 'text-white' : 'text-slate-300'}`}>
                        {role.label}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {formData.role === 'student' && (
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Sinif Seviyesi *
                  </label>
                  <select
                    name="grade"
                    value={formData.grade}
                    onChange={handleChange}
                    className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-purple-500 outline-none"
                    required
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
                  Okul (Opsiyonel)
                </label>
                <select
                  name="school_id"
                  value={formData.school_id}
                  onChange={handleChange}
                  className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-purple-500 outline-none"
                >
                  <option value="">Okul secin (sonra atanabilir)</option>
                  {schools.map((school) => (
                    <option key={school.id} value={school.id}>{school.name}</option>
                  ))}
                </select>
                <p className="mt-2 text-xs text-slate-500">
                  Kullanici daha sonra bir okula atanabilir
                </p>
              </div>
            </div>
          </div>

          {/* Ozet */}
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Ozet</h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Email:</span>
                <span className="text-white">{formData.email || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Isim:</span>
                <span className="text-white">{formData.full_name || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Rol:</span>
                <span className="text-white">
                  {formData.role === 'student' ? 'Ogrenci' : formData.role === 'teacher' ? 'Ogretmen' : 'Okul Admin'}
                </span>
              </div>
              {formData.role === 'student' && (
                <div className="flex justify-between">
                  <span className="text-slate-400">Sinif:</span>
                  <span className="text-white">{formData.grade ? `${formData.grade}. Sinif` : '-'}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-slate-400">Okul:</span>
                <span className="text-white">
                  {formData.school_id
                    ? schools.find(s => s.id === parseInt(formData.school_id))?.name
                    : 'Atanmadi'}
                </span>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-4">
            <button
              type="button"
              onClick={() => navigate('/admin/kullanicilar')}
              className="flex-1 px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium transition-colors"
            >
              Iptal
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-600/50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
            >
              {isLoading ? 'Olusturuluyor...' : 'Kullanici Olustur'}
            </button>
          </div>
        </form>
      </div>
    </AdminLayout>
  );
};

export default UserCreate;
