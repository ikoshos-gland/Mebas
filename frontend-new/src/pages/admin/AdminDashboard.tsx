/**
 * Platform Admin Dashboard
 * Overview of all schools and platform statistics
 */
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { AdminLayout } from '../../components/layout';
import type { SchoolWithStats, SchoolListResponse, TierInfo } from '../../types';
import api from '../../services/api';

const AdminDashboard = () => {
  const { user } = useAuth();
  const [schools, setSchools] = useState<SchoolWithStats[]>([]);
  const [tiers, setTiers] = useState<TierInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState({
    totalSchools: 0,
    activeSchools: 0,
    totalStudents: 0,
    totalTeachers: 0,
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      const [schoolsRes, tiersRes] = await Promise.all([
        api.get<SchoolListResponse>('/admin/schools'),
        api.get<TierInfo[]>('/admin/schools/tiers'),
      ]);

      setSchools(schoolsRes.data.items);
      setTiers(tiersRes.data);

      // Calculate stats
      const schoolList = schoolsRes.data.items;
      setStats({
        totalSchools: schoolList.length,
        activeSchools: schoolList.filter((s: SchoolWithStats) => s.is_active).length,
        totalStudents: schoolList.reduce((sum: number, s: SchoolWithStats) => sum + s.student_count, 0),
        totalTeachers: schoolList.reduce((sum: number, s: SchoolWithStats) => sum + s.teacher_count, 0),
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Veriler yuklenirken hata olustu');
    } finally {
      setIsLoading(false);
    }
  };

  const getTierBadgeColor = (tier: string) => {
    switch (tier) {
      case 'large': return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
      case 'medium': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  return (
    <AdminLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">
            Platform Yonetimi
          </h1>
          <p className="text-slate-400 mt-2">
            Hos geldiniz, {user?.full_name}
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Toplam Okul</p>
                <p className="text-3xl font-bold text-white mt-1">{stats.totalSchools}</p>
              </div>
              <div className="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Aktif Okul</p>
                <p className="text-3xl font-bold text-emerald-400 mt-1">{stats.activeSchools}</p>
              </div>
              <div className="w-12 h-12 bg-emerald-500/20 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Toplam Ogrenci</p>
                <p className="text-3xl font-bold text-white mt-1">{stats.totalStudents}</p>
              </div>
              <div className="w-12 h-12 bg-amber-500/20 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Toplam Ogretmen</p>
                <p className="text-3xl font-bold text-white mt-1">{stats.totalTeachers}</p>
              </div>
              <div className="w-12 h-12 bg-purple-500/20 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mb-8">
          <div className="flex flex-wrap gap-4">
            <Link
              to="/admin/okullar/yeni"
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              Yeni Okul Ekle
            </Link>
            <Link
              to="/admin/okullar"
              className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium transition-colors"
            >
              Tum Okullari Gor
            </Link>
          </div>
        </div>

        {/* Tier Info */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-white mb-4">Abonelik Paketleri</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {tiers.map((tier) => (
              <div
                key={tier.name}
                className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6"
              >
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-white capitalize">{tier.name}</h3>
                  <span className={`px-3 py-1 rounded-full text-sm border ${getTierBadgeColor(tier.name)}`}>
                    {tier.price_try.toLocaleString('tr-TR')} TL/ay
                  </span>
                </div>
                <ul className="space-y-2 text-sm text-slate-300">
                  <li className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    Max {tier.max_students} ogrenci
                  </li>
                  <li className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    Max {tier.max_teachers} ogretmen
                  </li>
                  <li className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    Max {tier.max_classrooms} sinif
                  </li>
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Schools */}
        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-white">Son Eklenen Okullar</h2>
            <Link
              to="/admin/okullar"
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
              <button onClick={fetchData} className="mt-4 text-blue-400 hover:text-blue-300">
                Tekrar Dene
              </button>
            </div>
          ) : schools.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-slate-400">Henuz okul eklenmemis</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-slate-400 text-sm border-b border-slate-700">
                    <th className="pb-3 font-medium">Okul</th>
                    <th className="pb-3 font-medium">Tier</th>
                    <th className="pb-3 font-medium">Ogrenci</th>
                    <th className="pb-3 font-medium">Ogretmen</th>
                    <th className="pb-3 font-medium">Durum</th>
                    <th className="pb-3 font-medium"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                  {schools.slice(0, 5).map((school) => (
                    <tr key={school.id} className="text-slate-300">
                      <td className="py-4">
                        <div>
                          <p className="font-medium text-white">{school.name}</p>
                          <p className="text-sm text-slate-400">{school.city || school.slug}</p>
                        </div>
                      </td>
                      <td className="py-4">
                        <span className={`px-2 py-1 rounded text-xs border ${getTierBadgeColor(school.tier)}`}>
                          {school.tier}
                        </span>
                      </td>
                      <td className="py-4">{school.student_count}</td>
                      <td className="py-4">{school.teacher_count}</td>
                      <td className="py-4">
                        {school.is_active ? (
                          <span className="text-emerald-400 text-sm">Aktif</span>
                        ) : (
                          <span className="text-red-400 text-sm">Pasif</span>
                        )}
                      </td>
                      <td className="py-4">
                        <Link
                          to={`/admin/okullar/${school.id}`}
                          className="text-blue-400 hover:text-blue-300 text-sm"
                        >
                          Detay
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </AdminLayout>
  );
};

export default AdminDashboard;
