import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GraduationCap, User, BookOpen, ChevronRight } from 'lucide-react';
import { Card, Button } from '../components/common';
import { useAuth } from '../context/AuthContext';
import { grades } from '../utils/theme';

type Role = 'student' | 'teacher';

const ProfileComplete = () => {
  const navigate = useNavigate();
  const { user, firebaseUser, completeProfile } = useAuth();
  const [step, setStep] = useState<'role' | 'grade'>('role');
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [selectedGrade, setSelectedGrade] = useState<number>(9);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // If already complete, redirect
  if (user?.profile_complete) {
    navigate('/panel', { replace: true });
    return null;
  }

  const handleRoleSelect = (role: Role) => {
    setSelectedRole(role);
    if (role === 'teacher') {
      handleSubmit(role);
    } else {
      setStep('grade');
    }
  };

  const handleSubmit = async (role?: Role) => {
    const finalRole = role || selectedRole;
    if (!finalRole) return;

    setIsLoading(true);
    setError(null);

    try {
      await completeProfile({
        role: finalRole,
        grade: finalRole === 'student' ? selectedGrade : undefined,
        full_name: firebaseUser?.displayName || undefined,
      });
      navigate('/panel', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bir hata olustu');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8 animate-enter">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-sepia/10 mb-4">
            <BookOpen className="w-8 h-8 text-sepia" />
          </div>
          <h1 className="font-serif-custom text-2xl text-ink mb-2">
            Profilinizi Tamamlayin
          </h1>
          <p className="text-neutral-600 text-sm">
            Size en uygun icerigi sunabilmemiz icin birka bilgiye ihtiyacimiz var.
          </p>
        </div>

        {/* Step: Role Selection */}
        {step === 'role' && (
          <div className="space-y-4 animate-enter">
            <p className="font-mono-custom text-[10px] uppercase tracking-widest text-neutral-500 text-center mb-4">
              Rolunuzu Secin
            </p>

            <button
              onClick={() => handleRoleSelect('student')}
              className="w-full p-6 rounded-xl border-2 border-stone-200 bg-paper hover:border-sepia hover:bg-sepia/5 transition-all text-left group"
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-sepia/10 flex items-center justify-center group-hover:bg-sepia/20 transition-colors">
                  <GraduationCap className="w-6 h-6 text-sepia" />
                </div>
                <div className="flex-1">
                  <h3 className="font-serif-custom text-lg text-ink mb-1">Ogrenci</h3>
                  <p className="text-sm text-neutral-600">
                    Ders calisiyorum, sorularima yardim istiyorum
                  </p>
                </div>
                <ChevronRight className="w-5 h-5 text-neutral-400 group-hover:text-sepia transition-colors" />
              </div>
            </button>

            <button
              onClick={() => handleRoleSelect('teacher')}
              disabled={isLoading}
              className="w-full p-6 rounded-xl border-2 border-stone-200 bg-paper hover:border-sepia hover:bg-sepia/5 transition-all text-left group disabled:opacity-50"
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-sepia/10 flex items-center justify-center group-hover:bg-sepia/20 transition-colors">
                  <User className="w-6 h-6 text-sepia" />
                </div>
                <div className="flex-1">
                  <h3 className="font-serif-custom text-lg text-ink mb-1">Ogretmen</h3>
                  <p className="text-sm text-neutral-600">
                    Ogrencilerime yardimci olmak istiyorum
                  </p>
                </div>
                <ChevronRight className="w-5 h-5 text-neutral-400 group-hover:text-sepia transition-colors" />
              </div>
            </button>
          </div>
        )}

        {/* Step: Grade Selection */}
        {step === 'grade' && (
          <Card variant="surface" className="animate-enter">
            <div className="flex items-center gap-2 mb-6">
              <button
                onClick={() => setStep('role')}
                className="text-neutral-500 hover:text-ink transition-colors"
              >
                <ChevronRight className="w-5 h-5 rotate-180" />
              </button>
              <h2 className="font-serif-custom text-xl text-ink">
                Sinif Seviyenizi Secin
              </h2>
            </div>

            <div className="space-y-4">
              {/* Grade Groups */}
              {['Ilkokul', 'Ortaokul', 'Lise'].map((level) => (
                <div key={level}>
                  <p className="font-mono-custom text-[10px] uppercase tracking-widest text-neutral-500 mb-2">
                    {level}
                  </p>
                  <div className="grid grid-cols-4 gap-2">
                    {grades
                      .filter((g) => g.level === level)
                      .map((g) => (
                        <button
                          key={g.value}
                          onClick={() => setSelectedGrade(g.value)}
                          className={`
                            p-3 rounded-lg border-2 text-center font-medium transition-all
                            ${selectedGrade === g.value
                              ? 'border-sepia bg-sepia/10 text-sepia'
                              : 'border-stone-200 bg-paper text-ink hover:border-sepia/50'
                            }
                          `}
                        >
                          {g.value}
                        </button>
                      ))}
                  </div>
                </div>
              ))}
            </div>

            {error && (
              <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
                {error}
              </div>
            )}

            <div className="mt-6 pt-4 border-t border-stone-200">
              <Button
                onClick={() => handleSubmit()}
                isLoading={isLoading}
                className="w-full"
              >
                Tamamla
              </Button>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
};

export default ProfileComplete;
