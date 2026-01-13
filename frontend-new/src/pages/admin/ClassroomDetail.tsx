/**
 * Classroom Detail Page
 * View and edit classroom information, manage students
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AdminLayout } from '../../components/layout';
import api from '../../services/api';

interface ClassroomDetail {
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

interface StudentItem {
  id: number;
  email: string;
  full_name: string;
  grade?: number;
  joined_at: string;
}

interface TeacherOption {
  id: number;
  full_name: string;
  email: string;
}

const ClassroomDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [classroom, setClassroom] = useState<ClassroomDetail | null>(null);
  const [students, setStudents] = useState<StudentItem[]>([]);
  const [teachers, setTeachers] = useState<TeacherOption[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [editData, setEditData] = useState({
    name: '',
    teacher_id: '',
    grade: '',
    subject: '',
  });

  useEffect(() => {
    fetchClassroom();
    fetchStudents();
  }, [id]);

  const fetchClassroom = async () => {
    try {
      setIsLoading(true);
      const response = await api.get<ClassroomDetail>(`/admin/classrooms/${id}`);
      setClassroom(response.data);
      setEditData({
        name: response.data.name,
        teacher_id: response.data.teacher_id.toString(),
        grade: response.data.grade.toString(),
        subject: response.data.subject || '',
      });
      // Fetch teachers from same school
      if (response.data.school_id) {
        fetchTeachers(response.data.school_id);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Sinif yuklenirken hata olustu');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchStudents = async () => {
    try {
      const response = await api.get<StudentItem[]>(`/admin/classrooms/${id}/students`);
      setStudents(response.data);
    } catch (err) {
      console.error('Failed to fetch students', err);
    }
  };

  const fetchTeachers = async (schoolId: number) => {
    try {
      const response = await api.get('/admin/users', {
        params: { school_id: schoolId, role: 'teacher', page_size: 100 }
      });
      setTeachers(response.data.items.map((t: any) => ({
        id: t.id,
        full_name: t.full_name,
        email: t.email
      })));
    } catch (err) {
      console.error('Failed to fetch teachers', err);
    }
  };

  const handleSave = async () => {
    if (!classroom) return;

    try {
      setIsSaving(true);
      setError(null);

      const payload: any = {
        name: editData.name,
        teacher_id: parseInt(editData.teacher_id),
        grade: parseInt(editData.grade),
        subject: editData.subject || null,
      };

      await api.put(`/admin/classrooms/${id}`, payload);
      setSuccessMessage('Sinif basariyla guncellendi');
      setIsEditing(false);
      fetchClassroom();

      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Guncelleme basarisiz');
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggleStatus = async () => {
    if (!classroom) return;

    try {
      await api.put(`/admin/classrooms/${id}`, { is_active: !classroom.is_active });
      setSuccessMessage(classroom.is_active ? 'Sinif devre disi birakildi' : 'Sinif aktif edildi');
      fetchClassroom();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Islem basarisiz');
    }
  };

  const handleRemoveStudent = async (studentId: number, studentName: string) => {
    if (!confirm(`"${studentName}" ogrencisini siniftan cikarmak istediginize emin misiniz?`)) return;

    try {
      await api.delete(`/admin/classrooms/${id}/students/${studentId}`);
      setSuccessMessage('Ogrenci siniftan cikarildi');
      fetchStudents();
      fetchClassroom();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Islem basarisiz');
    }
  };

  const handleDelete = async () => {
    if (!classroom) return;
    if (!confirm(`"${classroom.name}" sinifini silmek istediginize emin misiniz? Tum ogrenci kayitlari da silinecektir.`)) return;

    try {
      await api.delete(`/admin/classrooms/${id}`);
      navigate('/admin/siniflar');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Silme islemi basarisiz');
    }
  };

  const copyJoinCode = () => {
    if (classroom) {
      navigator.clipboard.writeText(classroom.join_code);
      setSuccessMessage('Katilim kodu kopyalandi');
      setTimeout(() => setSuccessMessage(null), 2000);
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

  if (!classroom) {
    return (
      <AdminLayout>
        <div className="max-w-3xl mx-auto px-4 py-8">
          <div className="text-center py-12">
            <p className="text-slate-400">Sinif bulunamadi</p>
            <button
              onClick={() => navigate('/admin/siniflar')}
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
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/admin/siniflar')}
            className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors mb-4"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Siniflara Don
          </button>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white">{classroom.name}</h1>
              <p className="text-slate-400 mt-1">{classroom.school_name}</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={copyJoinCode}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm flex items-center gap-2"
                title="Katilim Kodunu Kopyala"
              >
                <span className="font-mono">{classroom.join_code}</span>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
              {classroom.is_active ? (
                <span className="px-3 py-1 bg-emerald-500/20 text-emerald-400 rounded text-sm">
                  Aktif
                </span>
              ) : (
                <span className="px-3 py-1 bg-red-500/20 text-red-400 rounded text-sm">
                  Pasif
                </span>
              )}
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

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Classroom Info Card */}
            <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-semibold text-white">Sinif Bilgileri</h2>
                <button
                  onClick={() => setIsEditing(!isEditing)}
                  className="px-4 py-2 text-sm bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
                >
                  {isEditing ? 'Iptal' : 'Duzenle'}
                </button>
              </div>

              {isEditing ? (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Sinif Adi
                    </label>
                    <input
                      type="text"
                      value={editData.name}
                      onChange={(e) => setEditData(prev => ({ ...prev, name: e.target.value }))}
                      className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-purple-500 outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Ogretmen
                    </label>
                    <select
                      value={editData.teacher_id}
                      onChange={(e) => setEditData(prev => ({ ...prev, teacher_id: e.target.value }))}
                      className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-purple-500 outline-none"
                    >
                      {teachers.map((teacher) => (
                        <option key={teacher.id} value={teacher.id}>
                          {teacher.full_name} ({teacher.email})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        Sinif Seviyesi
                      </label>
                      <select
                        value={editData.grade}
                        onChange={(e) => setEditData(prev => ({ ...prev, grade: e.target.value }))}
                        className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-purple-500 outline-none"
                      >
                        {[...Array(12)].map((_, i) => (
                          <option key={i + 1} value={i + 1}>{i + 1}. Sinif</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        Ders
                      </label>
                      <input
                        type="text"
                        value={editData.subject}
                        onChange={(e) => setEditData(prev => ({ ...prev, subject: e.target.value }))}
                        className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-purple-500 outline-none"
                        placeholder="Opsiyonel"
                      />
                    </div>
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
                    <span className="text-slate-400">Okul</span>
                    <span className="text-white">{classroom.school_name}</span>
                  </div>
                  <div className="flex justify-between py-3 border-b border-slate-700">
                    <span className="text-slate-400">Ogretmen</span>
                    <span className="text-white">{classroom.teacher_name}</span>
                  </div>
                  <div className="flex justify-between py-3 border-b border-slate-700">
                    <span className="text-slate-400">Seviye</span>
                    <span className="text-white">{classroom.grade}. Sinif</span>
                  </div>
                  <div className="flex justify-between py-3 border-b border-slate-700">
                    <span className="text-slate-400">Ders</span>
                    <span className="text-white">{classroom.subject || '-'}</span>
                  </div>
                  <div className="flex justify-between py-3">
                    <span className="text-slate-400">Olusturulma</span>
                    <span className="text-white">
                      {new Date(classroom.created_at).toLocaleDateString('tr-TR')}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Students List */}
            <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-semibold text-white">
                  Ogrenciler ({students.length})
                </h2>
              </div>

              {students.length === 0 ? (
                <div className="text-center py-8 text-slate-400">
                  Henuz bu sinifta ogrenci yok
                </div>
              ) : (
                <div className="space-y-2">
                  {students.map((student) => (
                    <div
                      key={student.id}
                      className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg"
                    >
                      <div>
                        <p className="font-medium text-white">{student.full_name}</p>
                        <p className="text-sm text-slate-400">{student.email}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        {student.grade && (
                          <span className="text-sm text-slate-400">{student.grade}. Sinif</span>
                        )}
                        <button
                          onClick={() => handleRemoveStudent(student.id, student.full_name)}
                          className="p-2 hover:bg-red-500/20 rounded-lg transition-colors"
                          title="Siniftan Cikar"
                        >
                          <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Stats Card */}
            <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
              <h2 className="text-lg font-semibold text-white mb-4">Istatistikler</h2>
              <div className="space-y-4">
                <div className="bg-slate-700/50 rounded-lg p-4 text-center">
                  <p className="text-3xl font-bold text-purple-400">{classroom.student_count}</p>
                  <p className="text-sm text-slate-400 mt-1">Ogrenci</p>
                </div>
              </div>
            </div>

            {/* Actions Card */}
            <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
              <h2 className="text-lg font-semibold text-white mb-4">Islemler</h2>
              <div className="space-y-3">
                <button
                  onClick={handleToggleStatus}
                  className={`w-full px-4 py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
                    classroom.is_active
                      ? 'bg-amber-500/20 hover:bg-amber-500/30 text-amber-400'
                      : 'bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400'
                  }`}
                >
                  {classroom.is_active ? (
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
                  onClick={handleDelete}
                  className="w-full px-4 py-3 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  Sinifi Sil
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
};

export default ClassroomDetailPage;
