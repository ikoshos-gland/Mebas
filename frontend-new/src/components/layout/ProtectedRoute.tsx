import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { FullPageLoading } from '../common';

export const ProtectedRoute = () => {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  // Show loading state while checking auth
  if (isLoading) {
    return <FullPageLoading text="Oturum kontrol ediliyor..." />;
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    // Save the attempted URL for redirecting after login
    return <Navigate to="/giris" state={{ from: location }} replace />;
  }

  // Redirect to profile completion if profile not complete
  // (except if already on the profile completion page)
  if (user && !user.profile_complete && location.pathname !== '/profil-tamamla') {
    return <Navigate to="/profil-tamamla" replace />;
  }

  // Render child routes
  return <Outlet />;
};
