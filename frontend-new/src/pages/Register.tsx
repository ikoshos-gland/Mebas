import { useState } from 'react';
import { Link, useNavigate, Navigate } from 'react-router-dom';
import { Mail, Lock, User, AlertCircle, GraduationCap } from 'lucide-react';
import { FirebaseError } from 'firebase/app';
import { ParticleBackground } from '../components/background/ParticleBackground';
import { Button, Input, Card, FullPageLoading } from '../components/common';
import { useAuth } from '../context/AuthContext';
import { grades } from '../utils/theme';

type Step = 1 | 2;
type Role = 'student' | 'teacher';

const Register = () => {
  const navigate = useNavigate();
  const { register, loginWithGoogle, completeProfile, user, isAuthenticated, isLoading: isAuthLoading } = useAuth();

  // All hooks must be called before any conditional returns
  const [step, setStep] = useState<Step>(1);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState<Role>('student');
  const [grade, setGrade] = useState<number>(10);
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);

  // Redirect if already authenticated
  if (isAuthLoading) {
    return <FullPageLoading text="Kontrol ediliyor..." />;
  }

  if (isAuthenticated && user?.profile_complete) {
    return <Navigate to="/panel" replace />;
  }

  if (isAuthenticated && user && !user.profile_complete) {
    return <Navigate to="/profil-tamamla" replace />;
  }

  const getFirebaseErrorMessage = (error: FirebaseError): string => {
    switch (error.code) {
      case 'auth/email-already-in-use':
        return 'Bu e-posta adresi zaten kullaniliyor';
      case 'auth/invalid-email':
        return 'Gecersiz e-posta adresi';
      case 'auth/weak-password':
        return 'Sifre cok zayif. En az 6 karakter kullanin.';
      case 'auth/network-request-failed':
        return 'Baglanti hatasi. Internet baglantinizi kontrol edin.';
      default:
        return 'Kayit basarisiz. Lutfen tekrar deneyin.';
    }
  };

  const handleStep1Submit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Sifreler eslemiyor');
      return;
    }

    if (password.length < 6) {
      setError('Sifre en az 6 karakter olmali');
      return;
    }

    setStep(2);
  };

  const handleStep2Submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!acceptTerms) {
      setError('Kullanim kosullarini kabul etmelisiniz');
      return;
    }

    setIsLoading(true);

    try {
      // Register with Firebase
      await register(email, password, fullName);

      // Complete profile with role and grade
      await completeProfile({
        role,
        grade: role === 'student' ? grade : undefined,
        full_name: fullName,
      });

      navigate('/panel');
    } catch (err) {
      if (err instanceof FirebaseError) {
        setError(getFirebaseErrorMessage(err));
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Kayit basarisiz');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleRegister = async () => {
    setError('');
    setIsGoogleLoading(true);

    try {
      await loginWithGoogle();
      // Google users need to complete their profile
      navigate('/profil-tamamla');
    } catch (err) {
      if (err instanceof FirebaseError) {
        // User closed popup - not an error
        if (err.code === 'auth/popup-closed-by-user') {
          setIsGoogleLoading(false);
          return;
        }
        if (err.code === 'auth/cancelled-popup-request') {
          setIsGoogleLoading(false);
          return;
        }
        setError(getFirebaseErrorMessage(err));
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Google ile kayit basarisiz');
      }
    } finally {
      setIsGoogleLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-canvas relative overflow-hidden flex items-center justify-center px-4 py-12">
      <ParticleBackground opacity={0.5} />

      <div className="relative z-10 w-full max-w-md animate-enter">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-3">
            <div className="w-10 h-10 border border-ink/10 flex items-center justify-center rounded bg-paper relative overflow-hidden">
              <div className="absolute w-full h-[0.5px] bg-ink rotate-45" />
              <div className="absolute w-full h-[0.5px] bg-ink -rotate-45" />
            </div>
            <span className="font-serif-custom text-2xl text-ink">Yediiklim</span>
          </Link>
        </div>

        <Card variant="glass" padding="lg">
          <div className="text-center mb-8">
            <h1 className="font-serif-custom text-2xl text-ink mb-2">Hesap Olustur</h1>
            <p className="text-sm text-neutral-600">
              {step === 1 ? 'Giris bilgilerinizi girin' : 'Profil bilgilerinizi tamamlayin'}
            </p>
          </div>

          {/* Progress Indicator */}
          <div className="flex items-center justify-center gap-2 mb-6">
            <div className={`w-8 h-1 rounded-full ${step >= 1 ? 'bg-sepia' : 'bg-stone-200'}`} />
            <div className={`w-8 h-1 rounded-full ${step >= 2 ? 'bg-sepia' : 'bg-stone-200'}`} />
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 mb-6 bg-red-50 border border-red-200 rounded-xl text-sm text-red-600">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          {step === 1 ? (
            <form onSubmit={handleStep1Submit} className="space-y-4">
              <Input
                label="E-posta"
                type="email"
                placeholder="ornek@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                leftIcon={<Mail className="w-4 h-4" />}
                required
                disabled={isGoogleLoading}
              />

              <Input
                label="Sifre"
                type="password"
                placeholder="En az 6 karakter"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                leftIcon={<Lock className="w-4 h-4" />}
                hint="En az 6 karakter olmali"
                required
                disabled={isGoogleLoading}
              />

              <Input
                label="Sifre Tekrar"
                type="password"
                placeholder="Sifrenizi tekrar girin"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                leftIcon={<Lock className="w-4 h-4" />}
                required
                disabled={isGoogleLoading}
              />

              <Button type="submit" className="w-full" disabled={isGoogleLoading}>
                Devam Et
              </Button>
            </form>
          ) : (
            <form onSubmit={handleStep2Submit} className="space-y-4">
              <Input
                label="Ad Soyad"
                type="text"
                placeholder="Adiniz ve soyadiniz"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                leftIcon={<User className="w-4 h-4" />}
                required
                disabled={isLoading}
              />

              {/* Role Selection */}
              <div className="space-y-2">
                <label className="font-mono-custom text-[10px] uppercase tracking-widest text-neutral-500 block">
                  Rol
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setRole('student')}
                    disabled={isLoading}
                    className={`
                      p-4 rounded-xl border-2 transition-all text-center
                      ${role === 'student'
                        ? 'border-sepia bg-sepia/5'
                        : 'border-stone-200 hover:border-stone-300'
                      }
                      ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
                    `}
                  >
                    <GraduationCap className={`w-6 h-6 mx-auto mb-2 ${role === 'student' ? 'text-sepia' : 'text-neutral-400'}`} />
                    <span className={`text-sm font-medium ${role === 'student' ? 'text-sepia' : 'text-neutral-600'}`}>
                      Ogrenci
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setRole('teacher')}
                    disabled={isLoading}
                    className={`
                      p-4 rounded-xl border-2 transition-all text-center
                      ${role === 'teacher'
                        ? 'border-sepia bg-sepia/5'
                        : 'border-stone-200 hover:border-stone-300'
                      }
                      ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
                    `}
                  >
                    <User className={`w-6 h-6 mx-auto mb-2 ${role === 'teacher' ? 'text-sepia' : 'text-neutral-400'}`} />
                    <span className={`text-sm font-medium ${role === 'teacher' ? 'text-sepia' : 'text-neutral-600'}`}>
                      Ogretmen
                    </span>
                  </button>
                </div>
              </div>

              {/* Grade Selection (for students) */}
              {role === 'student' && (
                <div className="space-y-2">
                  <label className="font-mono-custom text-[10px] uppercase tracking-widest text-neutral-500 block">
                    Sinif
                  </label>
                  <div className="relative">
                    <select
                      value={grade}
                      onChange={(e) => setGrade(Number(e.target.value))}
                      disabled={isLoading}
                      className="w-full appearance-none bg-paper border border-stone-200 text-ink text-sm font-sans p-3 rounded-xl hover:border-ink/30 focus:outline-none focus:border-sepia transition-colors cursor-pointer disabled:opacity-50"
                    >
                      {grades.map((g) => (
                        <option key={g.value} value={g.value}>
                          {g.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              )}

              {/* Terms Checkbox */}
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={acceptTerms}
                  onChange={(e) => setAcceptTerms(e.target.checked)}
                  disabled={isLoading}
                  className="w-4 h-4 mt-0.5 rounded border-stone-300 text-sepia focus:ring-sepia"
                />
                <span className="text-sm text-neutral-600">
                  <Link to="/kullanim-kosullari" className="text-sepia hover:underline">
                    Kullanim Kosullari
                  </Link>
                  {' '}ve{' '}
                  <Link to="/gizlilik" className="text-sepia hover:underline">
                    Gizlilik Politikasi
                  </Link>
                  'ni kabul ediyorum.
                </span>
              </label>

              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => setStep(1)}
                  className="flex-1"
                  disabled={isLoading}
                >
                  Geri
                </Button>
                <Button type="submit" className="flex-1" isLoading={isLoading}>
                  Kayit Ol
                </Button>
              </div>
            </form>
          )}

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-stone-200" />
            </div>
            <div className="relative flex justify-center">
              <span className="px-4 bg-paper text-xs text-neutral-500 uppercase tracking-wider">
                veya
              </span>
            </div>
          </div>

          <Button
            variant="secondary"
            className="w-full"
            onClick={handleGoogleRegister}
            isLoading={isGoogleLoading}
            disabled={isLoading}
            leftIcon={
              <svg className="w-4 h-4" viewBox="0 0 24 24">
                <path
                  fill="currentColor"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="currentColor"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="currentColor"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="currentColor"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
            }
          >
            Google ile Kayit Ol
          </Button>

          <p className="text-center text-sm text-neutral-600 mt-6">
            Zaten hesabiniz var mi?{' '}
            <Link to="/giris" className="text-sepia hover:underline font-medium">
              Giris yapin
            </Link>
          </p>
        </Card>
      </div>
    </div>
  );
};

export default Register;
