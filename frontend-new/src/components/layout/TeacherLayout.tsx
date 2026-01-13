/**
 * Teacher Layout Component
 * Wraps teacher pages with consistent navbar and dark theme
 */
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import TeacherNavbar from './TeacherNavbar';

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface TeacherLayoutProps {
  children: ReactNode;
  title?: string;
  breadcrumbs?: BreadcrumbItem[];
  actions?: ReactNode;
}

const TeacherLayout = ({ children, title, breadcrumbs, actions }: TeacherLayoutProps) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <TeacherNavbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Breadcrumbs */}
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav className="mb-4">
            <ol className="flex items-center gap-2 text-sm">
              {breadcrumbs.map((item, index) => (
                <li key={index} className="flex items-center gap-2">
                  {index > 0 && (
                    <svg className="w-4 h-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  )}
                  {item.href ? (
                    <Link to={item.href} className="text-slate-400 hover:text-white transition-colors">
                      {item.label}
                    </Link>
                  ) : (
                    <span className="text-slate-300">{item.label}</span>
                  )}
                </li>
              ))}
            </ol>
          </nav>
        )}

        {/* Page Header */}
        {(title || actions) && (
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
            {title && (
              <h1 className="text-2xl sm:text-3xl font-bold text-white">{title}</h1>
            )}
            {actions && (
              <div className="flex items-center gap-3">
                {actions}
              </div>
            )}
          </div>
        )}

        {/* Page Content */}
        {children}
      </main>
    </div>
  );
};

export default TeacherLayout;
