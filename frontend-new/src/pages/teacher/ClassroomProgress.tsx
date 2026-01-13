/**
 * Classroom Progress Page
 * View kazanim progress for entire classroom
 * Includes analytics and export features
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { TeacherLayout } from '../../components/layout';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Download, Users, Target, TrendingUp, TrendingDown, Search } from 'lucide-react';
import api from '../../services/api';
import type { ClassProgressResponse, KazanimAnalyticsResponse, KazanimStatistic } from '../../types';

const CHART_COLORS = {
  understood: '#10b981',
  in_progress: '#f59e0b',
  tracked: '#3b82f6',
};

type TabType = 'students' | 'analytics';

const ClassroomProgress = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [progress, setProgress] = useState<ClassProgressResponse | null>(null);
  const [analytics, setAnalytics] = useState<KazanimAnalyticsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyticsLoading, setIsAnalyticsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'name' | 'understood'>('understood');
  const [activeTab, setActiveTab] = useState<TabType>('students');
  const [searchTerm, setSearchTerm] = useState('');
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    fetchProgress();
  }, [id]);

  useEffect(() => {
    if (activeTab === 'analytics' && !analytics) {
      fetchAnalytics();
    }
  }, [activeTab]);

  const fetchProgress = async () => {
    try {
      setIsLoading(true);
      const response = await api.get<ClassProgressResponse>(`/classrooms/${id}/progress`);
      setProgress(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ilerleme verileri yuklenirken hata olustu');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchAnalytics = async () => {
    try {
      setIsAnalyticsLoading(true);
      const response = await api.get<KazanimAnalyticsResponse>(`/classrooms/${id}/analytics`);
      setAnalytics(response.data);
    } catch (err: any) {
      console.error('Analytics fetch error:', err);
    } finally {
      setIsAnalyticsLoading(false);
    }
  };

  const handleExportCSV = async () => {
    try {
      setIsExporting(true);
      const response = await api.get(`/classrooms/${id}/export/csv`, {
        responseType: 'blob',
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `sinif_ilerleme_${id}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export error:', err);
    } finally {
      setIsExporting(false);
    }
  };

  const getProgressColor = (understood: number, total: number) => {
    if (total === 0) return 'text-slate-400 bg-slate-500/20';
    const percent = (understood / total) * 100;
    if (percent >= 70) return 'text-emerald-400 bg-emerald-500/20';
    if (percent >= 40) return 'text-amber-400 bg-amber-500/20';
    return 'text-red-400 bg-red-500/20';
  };

  const getMasteryColor = (rate: number) => {
    if (rate >= 70) return 'text-emerald-400';
    if (rate >= 40) return 'text-amber-400';
    return 'text-red-400';
  };

  const sortedStudents = progress?.students?.slice().sort((a, b) => {
    if (sortBy === 'name') return a.student_name.localeCompare(b.student_name);
    return b.understood_count - a.understood_count;
  }) || [];

  // Filter analytics kazanimlar by search
  const filteredKazanimlar = analytics?.all_kazanimlar?.filter((k) =>
    k.kazanim_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
    k.kazanim_description.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  // Calculate chart data
  const getStatusDistributionData = () => {
    if (!progress) return [];
    return [
      { name: 'Anladi', value: progress.aggregate.total_understood, color: CHART_COLORS.understood },
      { name: 'Calisiyor', value: progress.aggregate.total_in_progress, color: CHART_COLORS.in_progress },
      { name: 'Takipte', value: progress.aggregate.total_tracked, color: CHART_COLORS.tracked },
    ];
  };

  const getStudentProgressData = () => {
    if (!progress) return [];
    return sortedStudents.slice(0, 15).map((s) => ({
      name: s.student_name.split(' ')[0], // First name only for chart
      understood: s.understood_count,
      in_progress: s.in_progress_count,
      tracked: s.tracked_count,
    }));
  };

  if (isLoading) {
    return (
      <TeacherLayout>
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      </TeacherLayout>
    );
  }

  if (error || !progress) {
    return (
      <TeacherLayout>
        <div className="text-center py-20">
          <p className="text-red-400 mb-4">{error || 'Ilerleme verisi bulunamadi'}</p>
          <button
            onClick={() => navigate('/siniflar')}
            className="text-blue-400 hover:text-blue-300"
          >
            Siniflara Don
          </button>
        </div>
      </TeacherLayout>
    );
  }

  const statusDistributionData = getStatusDistributionData();
  const studentProgressData = getStudentProgressData();
  const totalKazanimlar = progress.aggregate.total_understood + progress.aggregate.total_in_progress + progress.aggregate.total_tracked;

  return (
    <TeacherLayout
      title="Sinif Ilerlemesi"
      breadcrumbs={[
        { label: 'Panel', href: '/ogretmen' },
        { label: 'Siniflar', href: '/siniflar' },
        { label: progress.classroom_name, href: `/siniflar/${id}` },
        { label: 'Ilerleme' }
      ]}
    >
      {/* Header with Export Button */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">{progress.classroom_name}</h1>
        <button
          onClick={handleExportCSV}
          disabled={isExporting}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white rounded-lg transition-colors"
        >
          <Download className="w-4 h-4" />
          {isExporting ? 'Indiriliyor...' : 'CSV Indir'}
        </button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
          <p className="text-slate-400 text-sm">Toplam Ogrenci</p>
          <p className="text-3xl font-bold text-white mt-1">{progress.total_students}</p>
        </div>
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-6">
          <p className="text-emerald-400 text-sm">Toplam Anladi</p>
          <p className="text-3xl font-bold text-emerald-400 mt-1">{progress.aggregate.total_understood}</p>
        </div>
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-6">
          <p className="text-amber-400 text-sm">Toplam Calisiyor</p>
          <p className="text-3xl font-bold text-amber-400 mt-1">{progress.aggregate.total_in_progress}</p>
        </div>
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-6">
          <p className="text-blue-400 text-sm">Toplam Takipte</p>
          <p className="text-3xl font-bold text-blue-400 mt-1">{progress.aggregate.total_tracked}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-700 mb-6">
        <button
          onClick={() => setActiveTab('students')}
          className={`flex items-center gap-2 px-6 py-3 text-sm font-medium transition-colors ${
            activeTab === 'students'
              ? 'text-blue-400 border-b-2 border-blue-400'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <Users className="w-4 h-4" />
          Ogrenci Ilerlemesi
        </button>
        <button
          onClick={() => setActiveTab('analytics')}
          className={`flex items-center gap-2 px-6 py-3 text-sm font-medium transition-colors ${
            activeTab === 'analytics'
              ? 'text-blue-400 border-b-2 border-blue-400'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <Target className="w-4 h-4" />
          Kazanim Analizi
        </button>
      </div>

      {/* Students Tab */}
      {activeTab === 'students' && (
        <>
          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {/* Status Distribution Pie Chart */}
            <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Durum Dagilimi</h3>
              {totalKazanimlar > 0 ? (
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={statusDistributionData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {statusDistributionData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1e293b',
                          border: '1px solid #334155',
                          borderRadius: '8px',
                        }}
                        formatter={(value: number, name: string) => [`${value} kazanim`, name]}
                      />
                      <Legend
                        formatter={(value: string) => {
                          const item = statusDistributionData.find(d => d.name === value);
                          const total = statusDistributionData.reduce((sum, d) => sum + d.value, 0);
                          const percent = item && total > 0 ? ((item.value / total) * 100).toFixed(0) : 0;
                          return `${value}: ${item?.value || 0} (%${percent})`;
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-[300px] flex items-center justify-center text-slate-400">
                  Henuz ilerleme verisi yok
                </div>
              )}
            </div>

            {/* Student Progress Bar Chart */}
            <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Ogrenci Bazli Ilerleme</h3>
              {studentProgressData.length > 0 ? (
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={studentProgressData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis
                        dataKey="name"
                        stroke="#94a3b8"
                        tick={{ fontSize: 10 }}
                        angle={-45}
                        textAnchor="end"
                        height={60}
                      />
                      <YAxis stroke="#94a3b8" />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1e293b',
                          border: '1px solid #334155',
                          borderRadius: '8px',
                        }}
                      />
                      <Legend />
                      <Bar dataKey="understood" name="Anladi" stackId="a" fill={CHART_COLORS.understood} />
                      <Bar dataKey="in_progress" name="Calisiyor" stackId="a" fill={CHART_COLORS.in_progress} />
                      <Bar dataKey="tracked" name="Takipte" stackId="a" fill={CHART_COLORS.tracked} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-[300px] flex items-center justify-center text-slate-400">
                  Henuz ogrenci verisi yok
                </div>
              )}
            </div>
          </div>

          {/* Student List */}
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">Ogrenci Detaylari</h2>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'name' | 'understood')}
                className="px-3 py-1 bg-slate-700 border border-slate-600 rounded text-white text-sm"
              >
                <option value="understood">Anladiga Gore</option>
                <option value="name">Ada Gore</option>
              </select>
            </div>

            {sortedStudents.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-slate-400">Henuz ogrenci verisi yok</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-700">
                {sortedStudents.map((student) => {
                  const total = student.understood_count + student.in_progress_count + student.tracked_count;
                  const understoodPercent = total > 0 ? (student.understood_count / total) * 100 : 0;
                  const inProgressPercent = total > 0 ? (student.in_progress_count / total) * 100 : 0;

                  return (
                    <div key={student.student_id} className="px-6 py-4 hover:bg-slate-700/30 transition-colors">
                      <div className="flex items-center justify-between mb-2">
                        <div>
                          <Link
                            to={`/siniflar/${id}/ogrenci/${student.student_id}`}
                            className="font-medium text-white hover:text-blue-400"
                          >
                            {student.student_name}
                          </Link>
                          <p className="text-sm text-slate-400">{student.email}</p>
                        </div>
                        <div className="text-right">
                          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getProgressColor(student.understood_count, total)}`}>
                            {total > 0 ? `${understoodPercent.toFixed(0)}%` : '-'}
                          </span>
                        </div>
                      </div>
                      {total > 0 && (
                        <>
                          <div className="flex items-center gap-2">
                            <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden flex">
                              <div
                                className="h-full bg-emerald-500"
                                style={{ width: `${understoodPercent}%` }}
                              />
                              <div
                                className="h-full bg-amber-500"
                                style={{ width: `${inProgressPercent}%` }}
                              />
                            </div>
                          </div>
                          <div className="flex gap-4 text-xs text-slate-400 mt-2">
                            <span className="text-emerald-400">{student.understood_count} anladi</span>
                            <span className="text-amber-400">{student.in_progress_count} calisiyor</span>
                            <span className="text-blue-400">{student.tracked_count} takipte</span>
                          </div>
                        </>
                      )}
                      {student.last_activity && (
                        <p className="text-xs text-slate-500 mt-2">
                          Son aktivite: {new Date(student.last_activity).toLocaleDateString('tr-TR')}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}

      {/* Analytics Tab */}
      {activeTab === 'analytics' && (
        <>
          {isAnalyticsLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            </div>
          ) : analytics ? (
            <>
              {/* Analytics Summary */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-8">
                <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
                  <p className="text-slate-400 text-sm">Ortalama Basari Orani</p>
                  <p className={`text-3xl font-bold mt-1 ${getMasteryColor(analytics.summary.avg_mastery_rate)}`}>
                    %{analytics.summary.avg_mastery_rate}
                  </p>
                </div>
                <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
                  <p className="text-slate-400 text-sm">Toplam Kazanim</p>
                  <p className="text-3xl font-bold text-white mt-1">{analytics.summary.total_unique_kazanimlar}</p>
                </div>
              </div>

              {/* Most/Least Understood */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                {/* Most Understood */}
                <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-6">
                  <h3 className="text-lg font-semibold text-emerald-400 mb-4 flex items-center gap-2">
                    <TrendingUp className="w-5 h-5" />
                    En Cok Anlasilanlar
                  </h3>
                  {analytics.most_understood.length > 0 ? (
                    <div className="space-y-3">
                      {analytics.most_understood.slice(0, 5).map((k, index) => (
                        <div key={k.kazanim_code} className="flex items-start gap-3">
                          <span className="text-emerald-400 font-mono text-sm w-6">{index + 1}.</span>
                          <div className="flex-1">
                            <p className="font-mono text-xs text-emerald-300 bg-emerald-500/20 px-2 py-0.5 rounded inline-block">
                              {k.kazanim_code}
                            </p>
                            <p className="text-sm text-slate-300 mt-1 line-clamp-2">
                              {k.kazanim_description}
                            </p>
                            <p className="text-xs text-emerald-400 mt-1">
                              %{k.mastery_rate} basari ({k.understood_count}/{k.total_students} ogrenci)
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-slate-400 text-sm">Henuz veri yok</p>
                  )}
                </div>

                {/* Least Understood */}
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6">
                  <h3 className="text-lg font-semibold text-red-400 mb-4 flex items-center gap-2">
                    <TrendingDown className="w-5 h-5" />
                    Zorluk Yasanan Kazanimlar
                  </h3>
                  {analytics.least_understood.length > 0 ? (
                    <div className="space-y-3">
                      {analytics.least_understood.slice(0, 5).map((k, index) => (
                        <div key={k.kazanim_code} className="flex items-start gap-3">
                          <span className="text-red-400 font-mono text-sm w-6">{index + 1}.</span>
                          <div className="flex-1">
                            <p className="font-mono text-xs text-red-300 bg-red-500/20 px-2 py-0.5 rounded inline-block">
                              {k.kazanim_code}
                            </p>
                            <p className="text-sm text-slate-300 mt-1 line-clamp-2">
                              {k.kazanim_description}
                            </p>
                            <p className="text-xs text-red-400 mt-1">
                              %{k.mastery_rate} basari ({k.understood_count}/{k.total_students} ogrenci)
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-slate-400 text-sm">Henuz veri yok</p>
                  )}
                </div>
              </div>

              {/* All Kazanimlar Table */}
              <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-700 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <h2 className="text-lg font-semibold text-white">Tum Kazanimlar</h2>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                      type="text"
                      placeholder="Kazanim ara..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm w-64"
                    />
                  </div>
                </div>

                {filteredKazanimlar.length === 0 ? (
                  <div className="text-center py-12">
                    <p className="text-slate-400">
                      {searchTerm ? 'Aramayla eslesme bulunamadi' : 'Henuz kazanim verisi yok'}
                    </p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-slate-700/50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">Kod</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">Aciklama</th>
                          <th className="px-6 py-3 text-center text-xs font-medium text-slate-400 uppercase">Anladi</th>
                          <th className="px-6 py-3 text-center text-xs font-medium text-slate-400 uppercase">Calisiyor</th>
                          <th className="px-6 py-3 text-center text-xs font-medium text-slate-400 uppercase">Takipte</th>
                          <th className="px-6 py-3 text-center text-xs font-medium text-slate-400 uppercase">Basari</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-700">
                        {filteredKazanimlar.map((k) => (
                          <tr key={k.kazanim_code} className="hover:bg-slate-700/30">
                            <td className="px-6 py-4">
                              <span className="font-mono text-xs text-blue-400 bg-blue-500/20 px-2 py-1 rounded">
                                {k.kazanim_code}
                              </span>
                            </td>
                            <td className="px-6 py-4 text-sm text-slate-300 max-w-md">
                              <p className="line-clamp-2">{k.kazanim_description}</p>
                            </td>
                            <td className="px-6 py-4 text-center text-emerald-400">{k.understood_count}</td>
                            <td className="px-6 py-4 text-center text-amber-400">{k.in_progress_count}</td>
                            <td className="px-6 py-4 text-center text-blue-400">{k.tracked_count}</td>
                            <td className="px-6 py-4 text-center">
                              <span className={`font-medium ${getMasteryColor(k.mastery_rate)}`}>
                                %{k.mastery_rate}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="text-center py-12">
              <p className="text-slate-400">Analiz verileri yuklenemedi</p>
            </div>
          )}
        </>
      )}
    </TeacherLayout>
  );
};

export default ClassroomProgress;
