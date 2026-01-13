import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastProvider } from './components/common';

// Pages
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Chat from './pages/Chat';
import Settings from './pages/Settings';
import Kazanimlar from './pages/Kazanimlar';
import Pricing from './pages/Pricing';
import ProfileComplete from './pages/ProfileComplete';
import NotFound from './pages/NotFound';

// Teacher Pages
import {
  TeacherDashboard,
  ClassroomList,
  ClassroomDetail as TeacherClassroomDetail,
  ClassroomProgress,
  StudentProgressDetail,
  AssignmentList,
  AssignmentCreate,
  AssignmentDetail
} from './pages/teacher';

// Admin Pages
import {
  AdminDashboard,
  SchoolManagement,
  SchoolCreate,
  SchoolDetail,
  UserManagement,
  UserCreate,
  UserDetail,
  ClassroomManagement,
  ClassroomCreate,
  ClassroomDetail as AdminClassroomDetail
} from './pages/admin';

// Student Pages
import { JoinClassroom, MyClassrooms } from './pages/student';

// Context
import { AuthProvider, useAuth } from './context/AuthContext';

// Protected Route wrapper
import { ProtectedRoute } from './components/layout/ProtectedRoute';

/**
 * Role-based Dashboard component
 * Redirects to the appropriate dashboard based on user role
 */
const RoleDashboard = () => {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/giris" replace />;
  }

  switch (user.role) {
    case 'platform_admin':
      return <AdminDashboard />;
    case 'school_admin':
      // School admins see teacher dashboard for now
      return <TeacherDashboard />;
    case 'teacher':
      return <TeacherDashboard />;
    case 'student':
    default:
      return <Dashboard />;
  }
};

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <AuthProvider>
          <Router>
            <Routes>
              {/* Public Routes */}
              <Route path="/" element={<Landing />} />
              <Route path="/giris" element={<Login />} />
              <Route path="/kayit" element={<Register />} />
              <Route path="/fiyatlar" element={<Pricing />} />

              {/* Protected Routes - All Authenticated Users */}
              <Route element={<ProtectedRoute />}>
                <Route path="/profil-tamamla" element={<ProfileComplete />} />
                <Route path="/panel" element={<RoleDashboard />} />
                <Route path="/sohbet" element={<Chat />} />
                <Route path="/sohbet/:id" element={<Chat />} />
                <Route path="/kazanimlar" element={<Kazanimlar />} />
                <Route path="/ayarlar" element={<Settings />} />
              </Route>

              {/* Student Routes */}
              <Route element={<ProtectedRoute allowedRoles={['student']} />}>
                <Route path="/sinifa-katil" element={<JoinClassroom />} />
                <Route path="/siniflarim" element={<MyClassrooms />} />
              </Route>

              {/* Teacher Routes */}
              <Route element={<ProtectedRoute allowedRoles={['teacher', 'school_admin', 'platform_admin']} />}>
                <Route path="/ogretmen" element={<TeacherDashboard />} />
                <Route path="/siniflar" element={<ClassroomList />} />
                <Route path="/siniflar/:id" element={<TeacherClassroomDetail />} />
                <Route path="/siniflar/:id/ilerleme" element={<ClassroomProgress />} />
                <Route path="/siniflar/:id/ogrenci/:studentId" element={<StudentProgressDetail />} />
                <Route path="/odevler" element={<AssignmentList />} />
                <Route path="/odevler/yeni" element={<AssignmentCreate />} />
                <Route path="/odevler/:id" element={<AssignmentDetail />} />
              </Route>

              {/* Platform Admin Routes */}
              <Route element={<ProtectedRoute allowedRoles={['platform_admin']} />}>
                <Route path="/admin" element={<AdminDashboard />} />
                <Route path="/admin/okullar" element={<SchoolManagement />} />
                <Route path="/admin/okullar/yeni" element={<SchoolCreate />} />
                <Route path="/admin/okullar/:id" element={<SchoolDetail />} />
                <Route path="/admin/kullanicilar" element={<UserManagement />} />
                <Route path="/admin/kullanicilar/yeni" element={<UserCreate />} />
                <Route path="/admin/kullanicilar/:id" element={<UserDetail />} />
                <Route path="/admin/siniflar" element={<ClassroomManagement />} />
                <Route path="/admin/siniflar/yeni" element={<ClassroomCreate />} />
                <Route path="/admin/siniflar/:id" element={<AdminClassroomDetail />} />
              </Route>

              {/* 404 */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Router>
        </AuthProvider>
      </ToastProvider>
    </QueryClientProvider>
  );
}

export default App;
