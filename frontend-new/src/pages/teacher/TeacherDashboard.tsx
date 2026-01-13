/**
 * Teacher Dashboard Page
 * Displays teacher's classrooms overview, stats, and activity feed
 */
import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { TeacherLayout } from '../../components/layout';
import type { Classroom, ClassroomListResponse } from '../../types';
import api from '../../services/api';

interface DashboardStats {
  total_classrooms: number;
  total_students: number;
  active_assignments: number;
  pending_submissions: number;
  avg_performance: number;
  this_week_activity: number;
}

interface ActivityItem {
  id: number;
  type: string;
  description: string;
  student_name?: string;
  classroom_name?: string;
  timestamp: string;
}

interface ActivityResponse {
  items: ActivityItem[];
  total: number;
}

const TeacherDashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [classrooms, setClassrooms] = useState<Classroom[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setIsLoading(true);

      // Fetch all data in parallel
      const [classroomsRes, statsRes, activityRes] = await Promise.all([
        api.get<ClassroomListResponse>('/classrooms'),
        api.get<DashboardStats>('/classrooms/dashboard/stats').catch(() => ({ data: null })),
        api.get<ActivityResponse>('/classrooms/dashboard/activity?limit=5').catch(() => ({ data: { items: [], total: 0 } }))
      ]);

      setClassrooms(classroomsRes.data.items);
      if (statsRes.data) setStats(statsRes.data);
      if (activityRes.data) setActivities(activityRes.data.items);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Veriler yuklenirken hata olustu');
    } finally {
      setIsLoading(false);
    }
  };

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'enrollment':
        return (
          <div className="w-8 h-8 bg-emerald-500/20 rounded-full flex items-center justify-center">
            <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
            </svg>
          </div>
        );
      case 'submission':
        return (
          <div className="w-8 h-8 bg-blue-500/20 rounded-full flex items-center justify-center">
            <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        );
      default:
        return (
          <div className="w-8 h-8 bg-slate-500/20 rounded-full flex items-center justify-center">
            <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        );
    }
  };

  const formatTimeAgo = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 60) return `${diffMins} dk once`;
    if (diffHours < 24) return `${diffHours} saat once`;
    if (diffDays < 7) return `${diffDays} gun once`;
    return date.toLocaleDateString('tr-TR');
  };

  return (
    <TeacherLayout
      title={`Hos Geldiniz, ${user?.full_name}`}
    >
      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {/* Classrooms Count */}
        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Siniflar</p>
              <p className="text-2xl font-bold text-white mt-1">
                {stats?.total_classrooms ?? classrooms.length}
              </p>
            </div>
            <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            </div>
          </div>
        </div>

        {/* Students Count */}
        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Ogrenciler</p>
              <p className="text-2xl font-bold text-white mt-1">
                {stats?.total_students ?? classrooms.reduce((sum, c) => sum + c.student_count, 0)}
              </p>
            </div>
            <div className="w-10 h-10 bg-emerald-500/20 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            </div>
          </div>
        </div>

        {/* Active Assignments */}
        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Aktif Odevler</p>
              <p className="text-2xl font-bold text-white mt-1">
                {stats?.active_assignments ?? 0}
              </p>
            </div>
            <div className="w-10 h-10 bg-purple-500/20 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
              </svg>
            </div>
          </div>
        </div>

        {/* Average Performance */}
        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Ort. Basari</p>
              <p className={`text-2xl font-bold mt-1 ${
                (stats?.avg_performance ?? 0) >= 70 ? 'text-emerald-400' :
                (stats?.avg_performance ?? 0) >= 50 ? 'text-amber-400' : 'text-red-400'
              }`}>
                %{stats?.avg_performance?.toFixed(0) ?? 0}
              </p>
            </div>
            <div className="w-10 h-10 bg-amber-500/20 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <Link
          to="/siniflar"
          className="bg-gradient-to-br from-blue-600/20 to-blue-700/10 border border-blue-500/30 rounded-xl p-5 hover:border-blue-500/50 transition-colors group"
        >
          <div className="w-12 h-12 bg-blue-500/20 rounded-xl flex items-center justify-center mb-4 group-hover:bg-blue-500/30 transition-colors">
            <svg className="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          </div>
          <h3 className="text-white font-semibold mb-1">Sinif Olustur</h3>
          <p className="text-slate-400 text-sm">Yeni bir sinif acin ve ogrencileri davet edin</p>
        </Link>

        <Link
          to="/odevler/yeni"
          className="bg-gradient-to-br from-emerald-600/20 to-emerald-700/10 border border-emerald-500/30 rounded-xl p-5 hover:border-emerald-500/50 transition-colors group"
        >
          <div className="w-12 h-12 bg-emerald-500/20 rounded-xl flex items-center justify-center mb-4 group-hover:bg-emerald-500/30 transition-colors">
            <svg className="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <h3 className="text-white font-semibold mb-1">Odev Olustur</h3>
          <p className="text-slate-400 text-sm">Siniflariniza yeni odev veya sinav dagitIn</p>
        </Link>

        <Link
          to="/sohbet"
          className="bg-gradient-to-br from-purple-600/20 to-purple-700/10 border border-purple-500/30 rounded-xl p-5 hover:border-purple-500/50 transition-colors group"
        >
          <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center mb-4 group-hover:bg-purple-500/30 transition-colors">
            <svg className="w-6 h-6 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
          <h3 className="text-white font-semibold mb-1">AI Asistan</h3>
          <p className="text-slate-400 text-sm">Sorularinizi yanıtlayin ve ogrencilere yardim edin</p>
        </Link>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Classrooms List */}
        <div className="lg:col-span-2 bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-white">Siniflarim</h2>
            <Link
              to="/siniflar"
              className="text-blue-400 hover:text-blue-300 text-sm font-medium"
            >
              Tumunu Gor
            </Link>
          </div>

          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            </div>
          ) : error ? (
            <div className="text-center py-8">
              <p className="text-red-400">{error}</p>
              <button
                onClick={fetchDashboardData}
                className="mt-4 text-blue-400 hover:text-blue-300"
              >
                Tekrar Dene
              </button>
            </div>
          ) : classrooms.length === 0 ? (
            <div className="text-center py-8">
              <div className="w-16 h-16 bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
              </div>
              <p className="text-slate-400 mb-4">Henuz sinif olusturmadiniz</p>
              <button
                onClick={() => navigate('/siniflar')}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
              >
                Ilk Sinifimi Olustur
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {classrooms.slice(0, 5).map((classroom) => (
                <Link
                  key={classroom.id}
                  to={`/siniflar/${classroom.id}`}
                  className="flex items-center justify-between bg-slate-700/50 hover:bg-slate-700 rounded-lg p-4 transition-colors group"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
                      <span className="text-blue-400 font-bold">{classroom.grade}</span>
                    </div>
                    <div>
                      <h3 className="font-medium text-white group-hover:text-blue-400 transition-colors">
                        {classroom.name}
                      </h3>
                      <p className="text-slate-400 text-sm">
                        {classroom.subject || 'Genel'} • {classroom.student_count} ogrenci
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="font-mono text-sm text-blue-400">{classroom.join_code}</span>
                    {!classroom.join_enabled && (
                      <p className="text-amber-400 text-xs mt-1">Kapali</p>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Activity Feed */}
        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-white">Son Aktiviteler</h2>
            {stats?.this_week_activity !== undefined && (
              <span className="text-xs text-slate-400">Bu hafta: {stats.this_week_activity}</span>
            )}
          </div>

          {activities.length === 0 ? (
            <div className="text-center py-8">
              <div className="w-12 h-12 bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-slate-400 text-sm">Henuz aktivite yok</p>
            </div>
          ) : (
            <div className="space-y-4">
              {activities.map((activity) => (
                <div key={activity.id} className="flex items-start gap-3">
                  {getActivityIcon(activity.type)}
                  <div className="flex-1 min-w-0">
                    <p className="text-white text-sm">{activity.description}</p>
                    <div className="flex items-center gap-2 mt-1">
                      {activity.classroom_name && (
                        <span className="text-xs text-slate-400">{activity.classroom_name}</span>
                      )}
                      <span className="text-xs text-slate-500">{formatTimeAgo(activity.timestamp)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pending Submissions Alert */}
          {stats && stats.pending_submissions > 0 && (
            <div className="mt-6 p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-amber-500/20 rounded-full flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="text-amber-400 text-sm font-medium">Bekleyen Teslimler</p>
                  <p className="text-slate-400 text-xs">{stats.pending_submissions} ogrenci henuz teslim etmedi</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Quick Tips */}
      <div className="mt-8 bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/20 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Ipuclari</h3>
        <ul className="grid grid-cols-1 md:grid-cols-3 gap-4 text-slate-300 text-sm">
          <li className="flex items-start gap-2">
            <span className="text-blue-400 mt-0.5">•</span>
            <span>Ogrenciler <span className="font-mono text-blue-400">Katilim Kodu</span> ile sinifa katilir</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-blue-400 mt-0.5">•</span>
            <span>Ilerleme sayfasindan ogrenci basarilarini takip edin</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-blue-400 mt-0.5">•</span>
            <span>Odevleri birden fazla sinifa ayni anda dagitabilirsiniz</span>
          </li>
        </ul>
      </div>
    </TeacherLayout>
  );
};

export default TeacherDashboard;
