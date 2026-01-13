/**
 * Assignment Create Page
 * Multi-step form for creating and distributing assignments
 */
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { TeacherLayout } from '../../components/layout';
import type {
  CreateAssignmentRequest,
  Classroom,
  ClassroomListResponse,
  Assignment
} from '../../types';
import api from '../../services/api';

type Step = 'info' | 'classrooms' | 'review';

const AssignmentCreate = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const preselectedClassroom = searchParams.get('classroom');

  const [currentStep, setCurrentStep] = useState<Step>('info');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState<CreateAssignmentRequest>({
    title: '',
    description: '',
    assignment_type: 'homework',
    target_kazanimlar: [],
    due_at: '',
  });

  // Classroom selection
  const [classrooms, setClassrooms] = useState<Classroom[]>([]);
  const [selectedClassrooms, setSelectedClassrooms] = useState<number[]>(
    preselectedClassroom ? [parseInt(preselectedClassroom)] : []
  );
  const [isLoadingClassrooms, setIsLoadingClassrooms] = useState(false);

  // Kazanim input
  const [kazanimInput, setKazanimInput] = useState('');

  useEffect(() => {
    if (currentStep === 'classrooms') {
      fetchClassrooms();
    }
  }, [currentStep]);

  const fetchClassrooms = async () => {
    try {
      setIsLoadingClassrooms(true);
      const response = await api.get<ClassroomListResponse>('/classrooms');
      setClassrooms(response.data.items);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Siniflar yuklenirken hata olustu');
    } finally {
      setIsLoadingClassrooms(false);
    }
  };

  const handleAddKazanim = () => {
    const code = kazanimInput.trim().toUpperCase();
    if (code && !formData.target_kazanimlar?.includes(code)) {
      setFormData({
        ...formData,
        target_kazanimlar: [...(formData.target_kazanimlar || []), code]
      });
      setKazanimInput('');
    }
  };

  const handleRemoveKazanim = (code: string) => {
    setFormData({
      ...formData,
      target_kazanimlar: formData.target_kazanimlar?.filter(k => k !== code) || []
    });
  };

  const handleClassroomToggle = (classroomId: number) => {
    if (selectedClassrooms.includes(classroomId)) {
      setSelectedClassrooms(selectedClassrooms.filter(id => id !== classroomId));
    } else {
      setSelectedClassrooms([...selectedClassrooms, classroomId]);
    }
  };

  const handleSelectAll = () => {
    if (selectedClassrooms.length === classrooms.length) {
      setSelectedClassrooms([]);
    } else {
      setSelectedClassrooms(classrooms.map(c => c.id));
    }
  };

  const handleSubmit = async () => {
    try {
      setIsSubmitting(true);
      setError(null);

      // Create assignment
      const assignmentResponse = await api.post<Assignment>('/assignments', formData);
      const assignmentId = assignmentResponse.data.id;

      // Distribute to classrooms
      if (selectedClassrooms.length > 0) {
        await api.post(`/assignments/${assignmentId}/distribute`, {
          classroom_ids: selectedClassrooms,
          due_at_override: formData.due_at || null
        });
      }

      navigate(`/odevler/${assignmentId}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Odev olusturulurken hata olustu');
    } finally {
      setIsSubmitting(false);
    }
  };

  const canProceedToClassrooms = formData.title.trim().length >= 3;
  const canProceedToReview = selectedClassrooms.length > 0;

  const steps = [
    { key: 'info', label: 'Bilgiler', number: 1 },
    { key: 'classrooms', label: 'Siniflar', number: 2 },
    { key: 'review', label: 'Onay', number: 3 },
  ] as const;

  return (
    <TeacherLayout
      title="Yeni Odev Olustur"
      breadcrumbs={[
        { label: 'Panel', href: '/ogretmen' },
        { label: 'Odevler', href: '/odevler' },
        { label: 'Yeni' }
      ]}
    >
      {/* Progress Steps */}
      <div className="mb-8">
        <div className="flex items-center justify-center">
          {steps.map((step, index) => (
            <div key={step.key} className="flex items-center">
              <div
                className={`flex items-center justify-center w-10 h-10 rounded-full font-semibold ${
                  currentStep === step.key
                    ? 'bg-blue-600 text-white'
                    : steps.findIndex(s => s.key === currentStep) > index
                    ? 'bg-emerald-500 text-white'
                    : 'bg-slate-700 text-slate-400'
                }`}
              >
                {steps.findIndex(s => s.key === currentStep) > index ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  step.number
                )}
              </div>
              <span
                className={`ml-2 text-sm font-medium ${
                  currentStep === step.key ? 'text-white' : 'text-slate-400'
                }`}
              >
                {step.label}
              </span>
              {index < steps.length - 1 && (
                <div className="w-20 h-0.5 mx-4 bg-slate-700">
                  <div
                    className={`h-full bg-emerald-500 transition-all ${
                      steps.findIndex(s => s.key === currentStep) > index ? 'w-full' : 'w-0'
                    }`}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
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

      {/* Step Content */}
      <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
        {currentStep === 'info' && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold text-white mb-6">Odev Bilgileri</h2>

            {/* Title */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Odev Basligi *
              </label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="ornegin: Parabol Konusu Odev"
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Aciklama (Opsiyonel)
              </label>
              <textarea
                value={formData.description || ''}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Odev hakkinda ek bilgiler..."
                rows={3}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none"
              />
            </div>

            {/* Type */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Odev Turu *
              </label>
              <div className="grid grid-cols-3 gap-3">
                {([
                  { value: 'homework', label: 'Odev', icon: '📝' },
                  { value: 'practice', label: 'Alistirma', icon: '📚' },
                  { value: 'exam', label: 'Sinav', icon: '📋' },
                ] as const).map((type) => (
                  <button
                    key={type.value}
                    type="button"
                    onClick={() => setFormData({ ...formData, assignment_type: type.value })}
                    className={`p-4 rounded-lg border transition-colors ${
                      formData.assignment_type === type.value
                        ? 'border-blue-500 bg-blue-500/20'
                        : 'border-slate-600 bg-slate-700 hover:bg-slate-600'
                    }`}
                  >
                    <span className="text-2xl mb-2 block">{type.icon}</span>
                    <span className="text-white font-medium">{type.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Due Date */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Son Teslim Tarihi (Opsiyonel)
              </label>
              <input
                type="datetime-local"
                value={formData.due_at || ''}
                onChange={(e) => setFormData({ ...formData, due_at: e.target.value })}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
              />
            </div>

            {/* Target Kazanimlar */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Hedef Kazanimlar (Opsiyonel)
              </label>
              <div className="flex gap-2 mb-3">
                <input
                  type="text"
                  value={kazanimInput}
                  onChange={(e) => setKazanimInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddKazanim())}
                  placeholder="ornegin: M.10.2.1"
                  className="flex-1 px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none font-mono"
                />
                <button
                  type="button"
                  onClick={handleAddKazanim}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                >
                  Ekle
                </button>
              </div>
              {formData.target_kazanimlar && formData.target_kazanimlar.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {formData.target_kazanimlar.map((code) => (
                    <span
                      key={code}
                      className="inline-flex items-center gap-1 px-3 py-1 bg-blue-500/20 text-blue-400 rounded-full text-sm font-mono"
                    >
                      {code}
                      <button
                        type="button"
                        onClick={() => handleRemoveKazanim(code)}
                        className="hover:text-red-400"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Navigation */}
            <div className="flex justify-between pt-6 border-t border-slate-700">
              <button
                type="button"
                onClick={() => navigate('/odevler')}
                className="px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium transition-colors"
              >
                Iptal
              </button>
              <button
                type="button"
                onClick={() => setCurrentStep('classrooms')}
                disabled={!canProceedToClassrooms}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
              >
                Devam
              </button>
            </div>
          </div>
        )}

        {currentStep === 'classrooms' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-white">Siniflari Sec</h2>
              <button
                type="button"
                onClick={handleSelectAll}
                className="text-sm text-blue-400 hover:text-blue-300"
              >
                {selectedClassrooms.length === classrooms.length ? 'Hepsini Kaldir' : 'Hepsini Sec'}
              </button>
            </div>

            {isLoadingClassrooms ? (
              <div className="flex justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
              </div>
            ) : classrooms.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-slate-400 mb-4">Henuz sinif olusturmadiniz</p>
                <button
                  onClick={() => navigate('/siniflar')}
                  className="text-blue-400 hover:text-blue-300"
                >
                  Sinif Olustur
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {classrooms.map((classroom) => (
                  <label
                    key={classroom.id}
                    className={`flex items-center gap-4 p-4 rounded-lg border cursor-pointer transition-colors ${
                      selectedClassrooms.includes(classroom.id)
                        ? 'border-blue-500 bg-blue-500/10'
                        : 'border-slate-600 bg-slate-700/50 hover:bg-slate-700'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedClassrooms.includes(classroom.id)}
                      onChange={() => handleClassroomToggle(classroom.id)}
                      className="w-5 h-5 rounded border-slate-500 bg-slate-600 text-blue-600 focus:ring-blue-500"
                    />
                    <div className="flex-1">
                      <p className="font-medium text-white">{classroom.name}</p>
                      <p className="text-sm text-slate-400">
                        {classroom.grade}. Sinif {classroom.subject && `• ${classroom.subject}`} • {classroom.student_count} ogrenci
                      </p>
                    </div>
                  </label>
                ))}
              </div>
            )}

            <p className="text-sm text-slate-400">
              {selectedClassrooms.length} sinif secildi
            </p>

            {/* Navigation */}
            <div className="flex justify-between pt-6 border-t border-slate-700">
              <button
                type="button"
                onClick={() => setCurrentStep('info')}
                className="px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium transition-colors"
              >
                Geri
              </button>
              <button
                type="button"
                onClick={() => setCurrentStep('review')}
                disabled={!canProceedToReview}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
              >
                Devam
              </button>
            </div>
          </div>
        )}

        {currentStep === 'review' && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold text-white mb-6">Ozet ve Onay</h2>

            <div className="space-y-4">
              <div className="p-4 bg-slate-700/50 rounded-lg">
                <p className="text-sm text-slate-400 mb-1">Baslik</p>
                <p className="text-white font-medium">{formData.title}</p>
              </div>

              {formData.description && (
                <div className="p-4 bg-slate-700/50 rounded-lg">
                  <p className="text-sm text-slate-400 mb-1">Aciklama</p>
                  <p className="text-white">{formData.description}</p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-slate-700/50 rounded-lg">
                  <p className="text-sm text-slate-400 mb-1">Tur</p>
                  <p className="text-white capitalize">
                    {formData.assignment_type === 'homework' ? 'Odev' :
                     formData.assignment_type === 'practice' ? 'Alistirma' : 'Sinav'}
                  </p>
                </div>

                <div className="p-4 bg-slate-700/50 rounded-lg">
                  <p className="text-sm text-slate-400 mb-1">Son Tarih</p>
                  <p className="text-white">
                    {formData.due_at
                      ? new Date(formData.due_at).toLocaleString('tr-TR')
                      : 'Belirtilmedi'}
                  </p>
                </div>
              </div>

              <div className="p-4 bg-slate-700/50 rounded-lg">
                <p className="text-sm text-slate-400 mb-2">Secilen Siniflar ({selectedClassrooms.length})</p>
                <div className="flex flex-wrap gap-2">
                  {classrooms
                    .filter(c => selectedClassrooms.includes(c.id))
                    .map(c => (
                      <span key={c.id} className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-full text-sm">
                        {c.name}
                      </span>
                    ))}
                </div>
              </div>

              {formData.target_kazanimlar && formData.target_kazanimlar.length > 0 && (
                <div className="p-4 bg-slate-700/50 rounded-lg">
                  <p className="text-sm text-slate-400 mb-2">Hedef Kazanimlar</p>
                  <div className="flex flex-wrap gap-2">
                    {formData.target_kazanimlar.map(code => (
                      <span key={code} className="px-2 py-1 bg-slate-600 rounded text-xs text-slate-300 font-mono">
                        {code}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Navigation */}
            <div className="flex justify-between pt-6 border-t border-slate-700">
              <button
                type="button"
                onClick={() => setCurrentStep('classrooms')}
                className="px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium transition-colors"
              >
                Geri
              </button>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="px-8 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-600/50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors flex items-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Olusturuluyor...
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Odevi Olustur
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </TeacherLayout>
  );
};

export default AssignmentCreate;
