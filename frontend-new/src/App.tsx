import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastProvider } from './components/common';

// Pages
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Chat from './pages/Chat';
import Settings from './pages/Settings';
import Pricing from './pages/Pricing';
import NotFound from './pages/NotFound';

// Context
import { AuthProvider } from './context/AuthContext';

// Protected Route wrapper
import { ProtectedRoute } from './components/layout/ProtectedRoute';

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

              {/* Protected Routes */}
              <Route element={<ProtectedRoute />}>
                <Route path="/panel" element={<Dashboard />} />
                <Route path="/sohbet" element={<Chat />} />
                <Route path="/sohbet/:id" element={<Chat />} />
                <Route path="/ayarlar" element={<Settings />} />
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
