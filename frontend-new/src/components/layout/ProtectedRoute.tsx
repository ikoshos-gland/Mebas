import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { FullPageLoading } from '../common';
import type { UserRole } from '../../types';

interface ProtectedRouteProps {
  allowedRoles?: UserRole[];
}

export const ProtectedRoute = ({ allowedRoles }: ProtectedRouteProps) => {
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

  // Check role-based access
  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    // Redirect to appropriate dashboard based on role
    const dashboardPath = getDashboardPathForRole(user.role);
    return <Navigate to={dashboardPath} replace />;
  }

  // Render child routes
  return <Outlet />;
};

/**
 * Get the appropriate dashboard path for a given role
 */
function getDashboardPathForRole(role: UserRole): string {
  switch (role) {
    case 'platform_admin':
      return '/admin';
    case 'school_admin':
      return '/ogretmen';
    case 'teacher':
      return '/ogretmen';
    case 'student':
    default:
      return '/panel';
  }
}
