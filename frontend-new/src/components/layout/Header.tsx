import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Menu, X, Plus, History, User, LogOut, Settings, LayoutDashboard } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../common';

interface HeaderProps {
  transparent?: boolean;
}

export const Header = ({ transparent = true }: HeaderProps) => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const { isAuthenticated, user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const isLanding = location.pathname === '/';

  const handleLogout = () => {
    logout();
    navigate('/');
    setIsUserMenuOpen(false);
  };

  return (
    <header
      className={`
        fixed top-0 w-full z-50 px-4 md:px-8 py-4
        ${transparent
          ? 'bg-gradient-to-b from-canvas via-canvas/90 to-transparent'
          : 'bg-paper/95 backdrop-blur-lg border-b border-stone-200'
        }
      `}
    >
      <div className="max-w-7xl mx-auto flex justify-between items-center">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-3 group">
          <div
            className="w-9 h-9 border border-ink/10 flex items-center justify-center rounded bg-paper relative overflow-hidden shadow-sm transition-transform group-hover:scale-95"
          >
            <div className="absolute w-full h-[0.5px] bg-ink rotate-45 group-hover:rotate-90 transition-transform duration-700 ease-in-out" />
            <div className="absolute w-full h-[0.5px] bg-ink -rotate-45 group-hover:-rotate-90 transition-transform duration-700 ease-in-out" />
          </div>

          <div className="flex flex-col">
            <span className="font-serif-custom text-xl tracking-tight font-medium text-ink">
              Yediiklim
            </span>
            <span className="font-mono-custom text-[9px] uppercase tracking-widest text-sepia">
              AI Asistan
            </span>
          </div>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-6">
          {isLanding && (
            <>
              <a href="#features" className="text-sm text-neutral-600 hover:text-ink transition-colors">
                Ozellikler
              </a>
              <a href="#pricing" className="text-sm text-neutral-600 hover:text-ink transition-colors">
                Fiyatlar
              </a>
              <a href="#faq" className="text-sm text-neutral-600 hover:text-ink transition-colors">
                SSS
              </a>
            </>
          )}
        </nav>

        {/* Right Side Actions */}
        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <>
              {/* Authenticated User Actions */}
              <Link to="/sohbet" className="hidden md:flex">
                <Button variant="secondary" size="sm" leftIcon={<History className="w-3.5 h-3.5" />}>
                  Gecmis
                </Button>
              </Link>

              <Link to="/sohbet">
                <Button size="sm" leftIcon={<Plus className="w-3.5 h-3.5" />}>
                  Yeni Sohbet
                </Button>
              </Link>

              {/* User Menu */}
              <div className="relative">
                <button
                  onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                  className="w-9 h-9 rounded-full bg-gradient-to-br from-sepia to-accent flex items-center justify-center text-paper shadow-lg hover:shadow-xl transition-shadow"
                >
                  {user?.full_name?.[0]?.toUpperCase() || <User className="w-4 h-4" />}
                </button>

                {isUserMenuOpen && (
                  <>
                    <div
                      className="fixed inset-0 z-40"
                      onClick={() => setIsUserMenuOpen(false)}
                    />
                    <div className="absolute right-0 mt-2 w-56 card-surface rounded-xl shadow-lg z-50 py-2 animate-enter">
                      <div className="px-4 py-3 border-b border-stone-200">
                        <p className="font-sans font-medium text-ink truncate">
                          {user?.full_name}
                        </p>
                        <p className="text-xs text-neutral-500 truncate">{user?.email}</p>
                      </div>

                      <div className="py-2">
                        <Link
                          to="/panel"
                          className="flex items-center gap-3 px-4 py-2 text-sm text-neutral-600 hover:bg-stone-50 hover:text-ink transition-colors"
                          onClick={() => setIsUserMenuOpen(false)}
                        >
                          <LayoutDashboard className="w-4 h-4" />
                          Panel
                        </Link>

                        {/* Role-specific links */}
                        {(user?.role === 'teacher' || user?.role === 'school_admin') && (
                          <>
                            <Link
                              to="/ogretmen"
                              className="flex items-center gap-3 px-4 py-2 text-sm text-neutral-600 hover:bg-stone-50 hover:text-ink transition-colors"
                              onClick={() => setIsUserMenuOpen(false)}
                            >
                              <LayoutDashboard className="w-4 h-4" />
                              Ogretmen Paneli
                            </Link>
                            <Link
                              to="/siniflar"
                              className="flex items-center gap-3 px-4 py-2 text-sm text-neutral-600 hover:bg-stone-50 hover:text-ink transition-colors"
                              onClick={() => setIsUserMenuOpen(false)}
                            >
                              <User className="w-4 h-4" />
                              Siniflarim
                            </Link>
                          </>
                        )}

                        {user?.role === 'platform_admin' && (
                          <>
                            <Link
                              to="/admin"
                              className="flex items-center gap-3 px-4 py-2 text-sm text-neutral-600 hover:bg-stone-50 hover:text-ink transition-colors"
                              onClick={() => setIsUserMenuOpen(false)}
                            >
                              <LayoutDashboard className="w-4 h-4" />
                              Admin Panel
                            </Link>
                            <Link
                              to="/admin/okullar"
                              className="flex items-center gap-3 px-4 py-2 text-sm text-neutral-600 hover:bg-stone-50 hover:text-ink transition-colors"
                              onClick={() => setIsUserMenuOpen(false)}
                            >
                              <User className="w-4 h-4" />
                              Okullar
                            </Link>
                          </>
                        )}

                        {user?.role === 'student' && (
                          <>
                            <Link
                              to="/siniflarim"
                              className="flex items-center gap-3 px-4 py-2 text-sm text-neutral-600 hover:bg-stone-50 hover:text-ink transition-colors"
                              onClick={() => setIsUserMenuOpen(false)}
                            >
                              <User className="w-4 h-4" />
                              Siniflarim
                            </Link>
                            <Link
                              to="/kazanimlar"
                              className="flex items-center gap-3 px-4 py-2 text-sm text-neutral-600 hover:bg-stone-50 hover:text-ink transition-colors"
                              onClick={() => setIsUserMenuOpen(false)}
                            >
                              <LayoutDashboard className="w-4 h-4" />
                              Kazanimlarim
                            </Link>
                          </>
                        )}

                        <Link
                          to="/ayarlar"
                          className="flex items-center gap-3 px-4 py-2 text-sm text-neutral-600 hover:bg-stone-50 hover:text-ink transition-colors"
                          onClick={() => setIsUserMenuOpen(false)}
                        >
                          <Settings className="w-4 h-4" />
                          Ayarlar
                        </Link>
                      </div>

                      <div className="border-t border-stone-200 pt-2">
                        <button
                          onClick={handleLogout}
                          className="flex items-center gap-3 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors w-full"
                        >
                          <LogOut className="w-4 h-4" />
                          Cikis Yap
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </>
          ) : (
            <>
              {/* Guest Actions */}
              <Link to="/giris" className="hidden md:block">
                <Button variant="ghost" size="sm">
                  Giris Yap
                </Button>
              </Link>
              <Link to="/kayit">
                <Button size="sm">Kayit Ol</Button>
              </Link>
            </>
          )}

          {/* Mobile Menu Toggle */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="md:hidden p-2 hover:bg-stone-100 rounded-lg transition-colors"
          >
            {isMobileMenuOpen ? (
              <X className="w-5 h-5 text-ink" />
            ) : (
              <Menu className="w-5 h-5 text-ink" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {isMobileMenuOpen && (
        <div className="md:hidden absolute top-full left-0 right-0 bg-paper border-b border-stone-200 shadow-lg animate-enter">
          <nav className="px-4 py-4 space-y-2">
            {isLanding && (
              <>
                <a
                  href="#features"
                  className="block py-2 text-neutral-600 hover:text-ink"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Ozellikler
                </a>
                <a
                  href="#pricing"
                  className="block py-2 text-neutral-600 hover:text-ink"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Fiyatlar
                </a>
                <a
                  href="#faq"
                  className="block py-2 text-neutral-600 hover:text-ink"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  SSS
                </a>
              </>
            )}

            {isAuthenticated ? (
              <>
                <Link
                  to="/panel"
                  className="block py-2 text-neutral-600 hover:text-ink"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Panel
                </Link>
                <Link
                  to="/sohbet"
                  className="block py-2 text-neutral-600 hover:text-ink"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Sohbet
                </Link>
                <Link
                  to="/ayarlar"
                  className="block py-2 text-neutral-600 hover:text-ink"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Ayarlar
                </Link>
                <button
                  onClick={handleLogout}
                  className="block py-2 text-red-600 w-full text-left"
                >
                  Cikis Yap
                </button>
              </>
            ) : (
              <Link
                to="/giris"
                className="block py-2 text-neutral-600 hover:text-ink"
                onClick={() => setIsMobileMenuOpen(false)}
              >
                Giris Yap
              </Link>
            )}
          </nav>
        </div>
      )}
    </header>
  );
};
