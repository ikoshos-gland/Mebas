import { Link } from 'react-router-dom';
import { Home, ArrowLeft, Search } from 'lucide-react';
import { ParticleBackground } from '../components/background/ParticleBackground';
import { Button, Card } from '../components/common';

const NotFound = () => {
  return (
    <div className="min-h-screen bg-canvas relative overflow-hidden flex items-center justify-center px-4">
      <ParticleBackground opacity={0.5} />

      <div className="relative z-10 max-w-md w-full text-center animate-enter">
        <Card variant="glass" padding="lg">
          {/* 404 Display */}
          <div className="mb-8">
            <h1 className="font-serif-custom text-8xl text-sepia/20 mb-2">404</h1>
            <h2 className="font-serif-custom text-2xl text-ink mb-2">Sayfa Bulunamadı</h2>
            <p className="text-neutral-600">
              Aradığınız sayfa mevcut değil veya taşınmış olabilir.
            </p>
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link to="/">
              <Button leftIcon={<Home className="w-4 h-4" />}>Ana Sayfa</Button>
            </Link>

            <Button
              variant="secondary"
              leftIcon={<ArrowLeft className="w-4 h-4" />}
              onClick={() => window.history.back()}
            >
              Geri Dön
            </Button>
          </div>

          {/* Search Suggestion */}
          <div className="mt-8 pt-6 border-t border-stone-200">
            <p className="text-sm text-neutral-500 mb-3">
              Aradığınızı bulamadınız mı?
            </p>
            <Link
              to="/sohbet"
              className="inline-flex items-center gap-2 text-sepia hover:underline text-sm"
            >
              <Search className="w-4 h-4" />
              AI ile soru sorun
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default NotFound;
