import { useState } from 'react';
import { Link, useNavigate, useLocation, Navigate } from 'react-router-dom';
import { Mail, Lock, AlertCircle } from 'lucide-react';
import { FirebaseError } from 'firebase/app';
import { ParticleBackground } from '../components/background/ParticleBackground';
import { Button, Input, Card, FullPageLoading } from '../components/common';
import { useAuth } from '../context/AuthContext';

const Login = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, loginWithGoogle, user, isAuthenticated, isLoading: isAuthLoading } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);

  // Get redirect URL from state
  const from = (location.state as { from?: Location })?.from?.pathname || '/panel';

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

  // Redirect helper - check profile completion
  const handleSuccessfulAuth = () => {
    // If profile not complete, redirect to profile completion
    // Otherwise redirect to intended destination
    if (user && !user.profile_complete) {
      navigate('/profil-tamamla', { replace: true });
    } else {
      navigate(from, { replace: true });
    }
  };

  const getFirebaseErrorMessage = (error: FirebaseError): string => {
    switch (error.code) {
      case 'auth/user-not-found':
      case 'auth/wrong-password':
      case 'auth/invalid-credential':
        return 'E-posta veya sifre hatali';
      case 'auth/invalid-email':
        return 'Gecersiz e-posta adresi';
      case 'auth/user-disabled':
        return 'Bu hesap devre disi birakilmis';
      case 'auth/too-many-requests':
        return 'Cok fazla basarisiz deneme. Lutfen daha sonra tekrar deneyin.';
      case 'auth/network-request-failed':
        return 'Baglanti hatasi. Internet baglantinizi kontrol edin.';
      default:
        return 'Giris basarisiz. Lutfen tekrar deneyin.';
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(email, password);
      handleSuccessfulAuth();
    } catch (err) {
      if (err instanceof FirebaseError) {
        setError(getFirebaseErrorMessage(err));
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Giris basarisiz');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setError('');
    setIsGoogleLoading(true);

    try {
      await loginWithGoogle();
      handleSuccessfulAuth();
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
        setError('Google ile giris basarisiz');
      }
    } finally {
      setIsGoogleLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-canvas relative overflow-hidden flex items-center justify-center px-4">
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
            <h1 className="font-serif-custom text-2xl text-ink mb-2">Hosgeldiniz</h1>
            <p className="text-sm text-neutral-600">Hesabiniza giris yapin</p>
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 mb-6 bg-red-50 border border-red-200 rounded-xl text-sm text-red-600">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="E-posta"
              type="email"
              placeholder="ornek@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              leftIcon={<Mail className="w-4 h-4" />}
              required
              disabled={isLoading || isGoogleLoading}
            />

            <Input
              label="Sifre"
              type="password"
              placeholder="Sifrenizi girin"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              leftIcon={<Lock className="w-4 h-4" />}
              required
              disabled={isLoading || isGoogleLoading}
            />

            <div className="flex items-center justify-end">
              <Link
                to="/sifremi-unuttum"
                className="text-sm text-sepia hover:underline"
              >
                Sifremi unuttum
              </Link>
            </div>

            <Button
              type="submit"
              className="w-full"
              isLoading={isLoading}
              disabled={isGoogleLoading}
            >
              Giris Yap
            </Button>
          </form>

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
            onClick={handleGoogleLogin}
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
            Google ile Giris Yap
          </Button>

          <p className="text-center text-sm text-neutral-600 mt-6">
            Hesabiniz yok mu?{' '}
            <Link to="/kayit" className="text-sepia hover:underline font-medium">
              Kayit olun
            </Link>
          </p>
        </Card>
      </div>
    </div>
  );
};

export default Login;
