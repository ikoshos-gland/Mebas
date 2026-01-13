/**
 * Admin Layout Component
 * Wraps admin pages with navbar and consistent styling
 */
import type { ReactNode } from 'react';
import AdminNavbar from './AdminNavbar';

interface AdminLayoutProps {
  children: ReactNode;
}

const AdminLayout = ({ children }: AdminLayoutProps) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <AdminNavbar />
      <main>
        {children}
      </main>
    </div>
  );
};

export default AdminLayout;
