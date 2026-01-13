/**
 * Create New Classroom Page
 * Form for platform admins to create a new classroom
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AdminLayout } from '../../components/layout';
import api from '../../services/api';

interface SchoolOption {
  id: number;
  name: string;
}

interface TeacherOption {
  id: number;
  full_name: string;
  email: string;
}

interface ClassroomFormData {
  name: string;
  school_id: string;
  teacher_id: string;
  grade: string;
  subject: string;
}

const ClassroomCreate = () => {
  const navigate = useNavigate();
  const [schools, setSchools] = useState<SchoolOption[]>([]);
  const [teachers, setTeachers] = useState<TeacherOption[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState<ClassroomFormData>({
    name: '',
    school_id: '',
    teacher_id: '',
    grade: '',
    subject: '',
  });

  useEffect(() => {
    fetchSchools();
  }, []);

  useEffect(() => {
    if (formData.school_id) {
      fetchTeachers(formData.school_id);
    } else {
      setTeachers([]);
      setFormData(prev => ({ ...prev, teacher_id: '' }));
    }
  }, [formData.school_id]);

  const fetchSchools = async () => {
    try {
      const response = await api.get('/admin/schools');
      setSchools(response.data.items.map((s: any) => ({ id: s.id, name: s.name })));
    } catch (err) {
      console.error('Failed to fetch schools', err);
    }
  };

  const fetchTeachers = async (schoolId: string) => {
    try {
      // Fetch teachers from the selected school
      const response = await api.get('/admin/users', {
        params: {
          school_id: parseInt(schoolId),
          role: 'teacher',
          page_size: 100
        }
      });
      setTeachers(response.data.items.map((t: any) => ({
        id: t.id,
        full_name: t.full_name,
        email: t.email
      })));
    } catch (err) {
      console.error('Failed to fetch teachers', err);
      setTeachers([]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const validateForm = (): string | null => {
    if (!formData.name) return 'Sinif adi zorunludur';
    if (!formData.school_id) return 'Okul secimi zorunludur';
    if (!formData.teacher_id) return 'Ogretmen secimi zorunludur';
    if (!formData.grade) return 'Sinif seviyesi zorunludur';
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
        name: formData.name,
        school_id: parseInt(formData.school_id),
        teacher_id: parseInt(formData.teacher_id),
        grade: parseInt(formData.grade),
      };

      if (formData.subject) {
        payload.subject = formData.subject;
      }

      await api.post('/admin/classrooms', payload);
      navigate('/admin/siniflar');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Sinif olusturulurken hata olustu');
    } finally {
      setIsLoading(false);
    }
  };

  const selectedSchool = schools.find(s => s.id === parseInt(formData.school_id));
  const selectedTeacher = teachers.find(t => t.id === parseInt(formData.teacher_id));

  return (
    <AdminLayout>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/admin/siniflar')}
            className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors mb-4"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Geri
          </button>
          <h1 className="text-3xl font-bold text-white">Yeni Sinif Olustur</h1>
          <p className="text-slate-400 mt-2">
            Sisteme yeni bir sinif ekleyin
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
          {/* Okul ve Ogretmen */}
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Okul ve Ogretmen</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Okul *
                </label>
                <select
                  name="school_id"
                  value={formData.school_id}
                  onChange={handleChange}
                  className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-purple-500 outline-none"
                  required
                >
                  <option value="">Okul secin</option>
                  {schools.map((school) => (
                    <option key={school.id} value={school.id}>{school.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Ogretmen *
                </label>
                <select
                  name="teacher_id"
                  value={formData.teacher_id}
                  onChange={handleChange}
                  className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-purple-500 outline-none disabled:opacity-50"
                  disabled={!formData.school_id}
                  required
                >
                  <option value="">
                    {!formData.school_id ? 'Once okul secin' : teachers.length === 0 ? 'Bu okulda ogretmen yok' : 'Ogretmen secin'}
                  </option>
                  {teachers.map((teacher) => (
                    <option key={teacher.id} value={teacher.id}>
                      {teacher.full_name} ({teacher.email})
                    </option>
                  ))}
                </select>
                {formData.school_id && teachers.length === 0 && (
                  <p className="mt-2 text-xs text-amber-400">
                    Bu okulda henuz ogretmen yok. Once ogretmen ekleyin.
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Sinif Bilgileri */}
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Sinif Bilgileri</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Sinif Adi *
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none"
                  placeholder="Ornek: 9-A Matematik"
                  required
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                    <option value="">Seviye secin</option>
                    {[...Array(12)].map((_, i) => (
                      <option key={i + 1} value={i + 1}>{i + 1}. Sinif</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Ders (Opsiyonel)
                  </label>
                  <input
                    type="text"
                    name="subject"
                    value={formData.subject}
                    onChange={handleChange}
                    className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none"
                    placeholder="Ornek: Matematik"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Ozet */}
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Ozet</h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Okul:</span>
                <span className="text-white">{selectedSchool?.name || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Ogretmen:</span>
                <span className="text-white">{selectedTeacher?.full_name || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Sinif Adi:</span>
                <span className="text-white">{formData.name || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Seviye:</span>
                <span className="text-white">{formData.grade ? `${formData.grade}. Sinif` : '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Ders:</span>
                <span className="text-white">{formData.subject || '-'}</span>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-4">
            <button
              type="button"
              onClick={() => navigate('/admin/siniflar')}
              className="flex-1 px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium transition-colors"
            >
              Iptal
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-600/50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
            >
              {isLoading ? 'Olusturuluyor...' : 'Sinif Olustur'}
            </button>
          </div>
        </form>
      </div>
    </AdminLayout>
  );
};

export default ClassroomCreate;
