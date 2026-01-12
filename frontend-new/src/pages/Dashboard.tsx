import { Link } from 'react-router-dom';
import {
  MessageSquare,
  Target,
  Flame,
  Plus,
  BookOpen,
  Lightbulb,
  ChevronRight,
  Clock,
  CheckCircle,
  Loader2,
} from 'lucide-react';
import { Header } from '../components/layout/Header';
import { Button, Card } from '../components/common';
import { useAuth } from '../context/AuthContext';
import { useProgress } from '../hooks/useProgress';
import { useConversations } from '../hooks/useConversations';
import { ProgressChart, KazanimCard, RecommendationsList } from '../components/progress';

// Helper function to format relative time in Turkish
const formatRelativeTime = (dateString: string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return 'Az once';
  if (diffMins < 60) return `${diffMins} dakika once`;
  if (diffHours < 24) return `${diffHours} saat once`;
  if (diffDays === 1) return 'Dun';
  if (diffDays < 7) return `${diffDays} gun once`;
  return date.toLocaleDateString('tr-TR');
};

const Dashboard = () => {
  const { user } = useAuth();
  const firstName = user?.full_name?.split(' ')[0] || 'Kullanici';

  // Get progress data
  const {
    progress,
    stats,
    recommendations,
    isLoading: isProgressLoading,
    understoodCount,
    trackedCount,
    inProgressCount,
  } = useProgress();

  // Get conversations data
  const {
    conversations,
    isLoading: isConversationsLoading,
  } = useConversations();

  // Calculate total for progress chart
  const totalProgress = progress.length;
  const isLoading = isProgressLoading;

  return (
    <div className="min-h-screen bg-canvas">
      <Header transparent={false} />

      <main className="pt-24 pb-12 px-4 md:px-8">
        <div className="max-w-6xl mx-auto">
          {/* Welcome Section */}
          <div className="mb-8 animate-enter">
            <h1 className="font-serif-custom text-3xl text-ink mb-2">
              Merhaba, {firstName}!
            </h1>
            <p className="text-neutral-600">
              Ogrenme yolculugunuzda bugun size nasil yardimci olabilirim?
            </p>
          </div>

          {/* Quick Actions */}
          <div className="grid md:grid-cols-3 gap-4 mb-8">
            <Link to="/sohbet">
              <Card
                variant="surface"
                hover
                className="flex items-center gap-4 animate-enter"
              >
                <div className="w-12 h-12 rounded-xl bg-sepia/10 flex items-center justify-center">
                  <Plus className="w-6 h-6 text-sepia" />
                </div>
                <div>
                  <h3 className="font-sans font-medium text-ink">Yeni Sohbet</h3>
                  <p className="text-sm text-neutral-500">Soru sor</p>
                </div>
              </Card>
            </Link>

            <Link to="/kazanimlar">
              <Card
                variant="surface"
                hover
                className="flex items-center gap-4 animate-enter animate-delay-100"
              >
                <div className="w-12 h-12 rounded-xl bg-amber-100 flex items-center justify-center">
                  <BookOpen className="w-6 h-6 text-amber-600" />
                </div>
                <div>
                  <h3 className="font-sans font-medium text-ink">Kazanimlar</h3>
                  <p className="text-sm text-neutral-500">Mufredati incele</p>
                </div>
              </Card>
            </Link>

            <Link to="/oneriler">
              <Card
                variant="surface"
                hover
                className="flex items-center gap-4 animate-enter animate-delay-200"
              >
                <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center">
                  <Lightbulb className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-sans font-medium text-ink">Oneriler</h3>
                  <p className="text-sm text-neutral-500">Calisma plani</p>
                </div>
              </Card>
            </Link>
          </div>

          <div className="grid lg:grid-cols-3 gap-8">
            {/* Stats Section */}
            <div className="lg:col-span-1 space-y-4">
              <h2 className="font-serif-custom text-lg italic text-sepia mb-4">
                Ilerleme Durumu
              </h2>

              {/* Progress Stats Cards */}
              <Card variant="surface" className="animate-enter animate-delay-100">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                    <CheckCircle className="w-5 h-5 text-green-600" />
                  </div>
                  <div>
                    <p className="font-mono-custom text-2xl text-ink">
                      {isLoading ? '-' : understoodCount}
                    </p>
                    <p className="text-xs text-neutral-500">Anlasildi</p>
                  </div>
                </div>
              </Card>

              <Card variant="surface" className="animate-enter animate-delay-200">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-amber-100 flex items-center justify-center">
                    <Target className="w-5 h-5 text-amber-600" />
                  </div>
                  <div>
                    <p className="font-mono-custom text-2xl text-ink">
                      {isLoading ? '-' : trackedCount + inProgressCount}
                    </p>
                    <p className="text-xs text-neutral-500">Takipte</p>
                  </div>
                </div>
              </Card>

              <Card variant="surface" className="animate-enter animate-delay-300">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-orange-100 flex items-center justify-center">
                    <Flame className="w-5 h-5 text-orange-500" />
                  </div>
                  <div>
                    <p className="font-mono-custom text-2xl text-ink">
                      {isLoading ? '-' : stats?.streak_days || 0}
                    </p>
                    <p className="text-xs text-neutral-500">Gun Seri</p>
                  </div>
                </div>
              </Card>

              {/* Progress Chart */}
              <div className="animate-enter animate-delay-400">
                <ProgressChart
                  stats={stats}
                  understoodCount={understoodCount}
                  totalCount={totalProgress}
                />
              </div>
            </div>

            {/* Main Content Area */}
            <div className="lg:col-span-2 space-y-6">
              {/* Kazanim Progress List */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-serif-custom text-lg italic text-sepia">
                    Kazanim Takibi
                  </h2>
                  {progress.length > 0 && (
                    <span className="text-sm text-neutral-500">
                      {progress.length} kazanim
                    </span>
                  )}
                </div>

                {isLoading ? (
                  <Card variant="outlined" className="flex items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 text-sepia animate-spin" />
                  </Card>
                ) : progress.length > 0 ? (
                  <div className="space-y-3">
                    {progress.slice(0, 5).map((item, index) => (
                      <div
                        key={item.kazanim_code}
                        className="animate-enter"
                        style={{ animationDelay: `${(index + 1) * 0.1}s` }}
                      >
                        <KazanimCard progress={item} />
                      </div>
                    ))}
                    {progress.length > 5 && (
                      <Link to="/kazanimlar" className="block">
                        <Card
                          variant="outlined"
                          hover
                          className="flex items-center justify-center py-3 text-sm text-sepia"
                        >
                          +{progress.length - 5} daha fazla goster
                          <ChevronRight className="w-4 h-4 ml-1" />
                        </Card>
                      </Link>
                    )}
                  </div>
                ) : (
                  <Card variant="outlined" className="text-center py-12">
                    <Target className="w-12 h-12 text-neutral-300 mx-auto mb-4" />
                    <p className="text-neutral-500 mb-2">Henuz takip edilen kazanim yok</p>
                    <p className="text-sm text-neutral-400 mb-4">
                      Sohbette soru sordukca yuksek guvenli kazanimlar otomatik olarak buraya eklenir
                    </p>
                    <Link to="/sohbet">
                      <Button size="sm">Ilk Sorunuzu Sorun</Button>
                    </Link>
                  </Card>
                )}
              </div>

              {/* Recommendations */}
              {recommendations.length > 0 && (
                <div className="animate-enter animate-delay-300">
                  <RecommendationsList recommendations={recommendations} />
                </div>
              )}

              {/* Recent Conversations */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-serif-custom text-lg italic text-sepia">
                    Son Sohbetler
                  </h2>
                  <Link to="/sohbet" className="text-sm text-sepia hover:underline">
                    Tumunu Gor
                  </Link>
                </div>

                <div className="space-y-3">
                  {isConversationsLoading ? (
                    <Card variant="outlined" className="flex items-center justify-center py-12">
                      <Loader2 className="w-8 h-8 text-sepia animate-spin" />
                    </Card>
                  ) : conversations.length > 0 ? (
                    <>
                      {conversations.slice(0, 5).map((conversation, index) => (
                        <Link to={`/sohbet/${conversation.id}`} key={conversation.id}>
                          <Card
                            variant="surface"
                            hover
                            className="flex items-center justify-between animate-enter"
                            style={{ animationDelay: `${(index + 1) * 0.1}s` }}
                          >
                            <div className="flex items-center gap-4">
                              <div className="w-10 h-10 rounded-lg bg-stone-100 flex items-center justify-center">
                                <MessageSquare className="w-5 h-5 text-neutral-400" />
                              </div>
                              <div>
                                <h3 className="font-sans font-medium text-ink text-sm">
                                  {conversation.title}
                                </h3>
                                <div className="flex items-center gap-2 mt-1">
                                  {conversation.subject && (
                                    <>
                                      <span className="text-xs text-sepia font-mono-custom">
                                        {conversation.subject}
                                      </span>
                                      <span className="text-neutral-300">|</span>
                                    </>
                                  )}
                                  <span className="text-xs text-neutral-400 flex items-center gap-1">
                                    <Clock className="w-3 h-3" />
                                    {formatRelativeTime(conversation.updated_at || conversation.created_at)}
                                  </span>
                                </div>
                              </div>
                            </div>
                            <ChevronRight className="w-5 h-5 text-neutral-300" />
                          </Card>
                        </Link>
                      ))}
                    </>
                  ) : (
                    <Card variant="outlined" className="text-center py-12">
                      <MessageSquare className="w-12 h-12 text-neutral-300 mx-auto mb-4" />
                      <p className="text-neutral-500 mb-4">Henuz sohbet yok</p>
                      <Link to="/sohbet">
                        <Button size="sm">Ilk Sorunuzu Sorun</Button>
                      </Link>
                    </Card>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
