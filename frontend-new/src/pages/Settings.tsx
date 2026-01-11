import { useState, useEffect } from 'react';
import { User, Lock, Bell, CreditCard, Shield, Info, BookOpen, GraduationCap } from 'lucide-react';
import { Header } from '../components/layout/Header';
import { Card, Button, Input } from '../components/common';
import { useAuth } from '../context/AuthContext';
import { grades, subjects, examModes } from '../utils/theme';

type TabId = 'profile' | 'preferences' | 'subscription' | 'security';

const tabs = [
  { id: 'profile' as TabId, label: 'Profil', icon: User },
  { id: 'preferences' as TabId, label: 'Tercihler', icon: Bell },
  { id: 'subscription' as TabId, label: 'Abonelik', icon: CreditCard },
  { id: 'security' as TabId, label: 'Güvenlik', icon: Shield },
];

const Settings = () => {
  const { user, updateUser, logout } = useAuth();
  const [activeTab, setActiveTab] = useState<TabId>('profile');
  const [isLoading, setIsLoading] = useState(false);

  // Profile form state
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [gradeValue, setGradeValue] = useState(() => {
    const saved = localStorage.getItem('meba_grade');
    return saved ? Number(saved) : (user?.grade || 9);
  });

  // Preferences state - synced with localStorage (shared with Chat)
  const [defaultSubject, setDefaultSubject] = useState(() => {
    return localStorage.getItem('meba_subject') || 'Biyoloji';
  });
  const [isExamMode, setIsExamMode] = useState(() => {
    return localStorage.getItem('meba_exam_mode') === 'true';
  });
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [studyReminders, setStudyReminders] = useState(true);

  // Security state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Sync preferences to localStorage when they change
  useEffect(() => {
    localStorage.setItem('meba_grade', String(gradeValue));
  }, [gradeValue]);

  useEffect(() => {
    localStorage.setItem('meba_subject', defaultSubject);
  }, [defaultSubject]);

  useEffect(() => {
    localStorage.setItem('meba_exam_mode', String(isExamMode));
  }, [isExamMode]);

  const handleSaveProfile = async () => {
    setIsLoading(true);
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));
    updateUser({ full_name: fullName, grade: gradeValue });
    // Also update localStorage
    localStorage.setItem('meba_grade', String(gradeValue));
    setIsLoading(false);
  };

  const handleSavePreferences = async () => {
    setIsLoading(true);
    // Settings are already synced to localStorage via useEffect
    await new Promise((resolve) => setTimeout(resolve, 500));
    setIsLoading(false);
  };

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      alert('Şifreler eşleşmiyor');
      return;
    }
    setIsLoading(true);
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setIsLoading(false);
  };

  return (
    <div className="min-h-screen bg-canvas">
      <Header transparent={false} />

      <main className="pt-24 pb-12 px-4 md:px-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="font-serif-custom text-3xl text-ink mb-8 animate-enter">
            Ayarlar
          </h1>

          <div className="grid md:grid-cols-4 gap-6">
            {/* Sidebar */}
            <div className="md:col-span-1">
              <Card variant="surface" padding="sm" className="animate-enter">
                <nav className="space-y-1">
                  {tabs.map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`
                        w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors text-left
                        ${activeTab === tab.id
                          ? 'bg-sepia/10 text-sepia'
                          : 'text-neutral-600 hover:bg-stone-50 hover:text-ink'
                        }
                      `}
                    >
                      <tab.icon className="w-4 h-4" />
                      <span className="text-sm font-medium">{tab.label}</span>
                    </button>
                  ))}
                </nav>
              </Card>
            </div>

            {/* Content */}
            <div className="md:col-span-3">
              {/* Profile Tab */}
              {activeTab === 'profile' && (
                <Card variant="surface" className="animate-enter">
                  <h2 className="font-serif-custom text-xl italic text-sepia mb-6">
                    Profil Bilgileri
                  </h2>

                  <div className="space-y-6">
                    <Input
                      label="Ad Soyad"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      leftIcon={<User className="w-4 h-4" />}
                    />

                    <Input
                      label="E-posta"
                      type="email"
                      value={user?.email || ''}
                      disabled
                      hint="E-posta değiştirilemez"
                    />

                    <div className="space-y-2">
                      <label className="font-mono-custom text-[10px] uppercase tracking-widest text-neutral-500 flex items-center gap-1">
                        <GraduationCap className="w-3 h-3" />
                        Sınıf Seviyesi
                      </label>
                      <select
                        value={gradeValue}
                        onChange={(e) => setGradeValue(Number(e.target.value))}
                        className="w-full appearance-none bg-paper border border-stone-200 text-ink text-sm font-sans p-3 rounded-xl hover:border-ink/30 focus:outline-none focus:border-sepia focus:ring-1 focus:ring-sepia/20 transition-colors"
                      >
                        <optgroup label="İlkokul">
                          {grades.filter(g => g.level === 'İlkokul').map((g) => (
                            <option key={g.value} value={g.value}>{g.label}</option>
                          ))}
                        </optgroup>
                        <optgroup label="Ortaokul">
                          {grades.filter(g => g.level === 'Ortaokul').map((g) => (
                            <option key={g.value} value={g.value}>{g.label}</option>
                          ))}
                        </optgroup>
                        <optgroup label="Lise">
                          {grades.filter(g => g.level === 'Lise').map((g) => (
                            <option key={g.value} value={g.value}>{g.label}</option>
                          ))}
                        </optgroup>
                      </select>
                    </div>

                    <div className="flex justify-end pt-4 border-t border-stone-200">
                      <Button onClick={handleSaveProfile} isLoading={isLoading}>
                        Kaydet
                      </Button>
                    </div>
                  </div>
                </Card>
              )}

              {/* Preferences Tab */}
              {activeTab === 'preferences' && (
                <Card variant="surface" className="animate-enter">
                  <h2 className="font-serif-custom text-xl italic text-sepia mb-6">
                    Tercihler
                  </h2>

                  <div className="space-y-6">
                    {/* Default Subject */}
                    <div className="space-y-2">
                      <label className="font-mono-custom text-[10px] uppercase tracking-widest text-neutral-500 flex items-center gap-1">
                        <BookOpen className="w-3 h-3" />
                        Varsayılan Ders
                      </label>
                      <select
                        value={defaultSubject}
                        onChange={(e) => setDefaultSubject(e.target.value)}
                        className="w-full appearance-none bg-paper border border-stone-200 text-ink text-sm font-sans p-3 rounded-xl hover:border-ink/30 focus:outline-none focus:border-sepia focus:ring-1 focus:ring-sepia/20 transition-colors"
                      >
                        {subjects.map((s) => (
                          <option key={s.value} value={s.value}>
                            {s.icon} {s.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Exam Mode Section */}
                    <div className="space-y-4 p-4 rounded-xl bg-stone-50 border border-stone-200">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{isExamMode ? examModes.yks.icon : examModes.school.icon}</span>
                          <div>
                            <h3 className="font-sans font-medium text-ink">
                              {isExamMode ? 'YKS/Sınav Modu' : 'Okul Modu'}
                            </h3>
                            <p className="text-xs text-neutral-500">İçerik filtreleme modu</p>
                          </div>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={isExamMode}
                            onChange={(e) => setIsExamMode(e.target.checked)}
                            className="sr-only peer"
                          />
                          <div className="w-11 h-6 bg-stone-300 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-sepia/20 rounded-full peer peer-checked:bg-sepia transition-colors">
                            <span className="absolute top-[2px] left-[2px] bg-paper h-5 w-5 rounded-full transition-transform duration-300 peer-checked:translate-x-5 shadow-sm" />
                          </div>
                        </label>
                      </div>

                      {/* Mode description */}
                      <div className={`flex items-start gap-2 p-3 rounded-lg text-sm ${
                        isExamMode ? 'bg-sepia/10 text-sepia border border-sepia/20' : 'bg-white text-neutral-600 border border-stone-200'
                      }`}>
                        <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
                        <div>
                          <p className="font-medium mb-1">
                            {isExamMode ? examModes.yks.label : examModes.school.label}
                          </p>
                          <p className="text-xs leading-relaxed">
                            {isExamMode
                              ? examModes.yks.description
                              : examModes.school.description
                            }
                          </p>
                        </div>
                      </div>

                      {/* Content scope indicator */}
                      <div className="flex items-center justify-between text-xs pt-2 border-t border-stone-200">
                        <span className="text-neutral-500">İçerik Kapsamı:</span>
                        <span className={`font-medium ${isExamMode ? 'text-sepia' : 'text-ink'}`}>
                          {isExamMode
                            ? `1. Sınıf - ${gradeValue}. Sınıf (Kümülatif)`
                            : `Sadece ${gradeValue}. Sınıf`
                          }
                        </span>
                      </div>
                    </div>

                    {/* Notifications */}
                    <div className="space-y-4">
                      <h3 className="font-mono-custom text-[10px] uppercase tracking-widest text-neutral-500">
                        Bildirimler
                      </h3>

                      <label className="flex items-center justify-between cursor-pointer p-3 rounded-xl border border-stone-200 hover:bg-stone-50 transition-colors">
                        <span className="text-sm text-ink">E-posta Bildirimleri</span>
                        <input
                          type="checkbox"
                          checked={emailNotifications}
                          onChange={(e) => setEmailNotifications(e.target.checked)}
                          className="w-4 h-4 rounded border-stone-300 text-sepia focus:ring-sepia"
                        />
                      </label>

                      <label className="flex items-center justify-between cursor-pointer p-3 rounded-xl border border-stone-200 hover:bg-stone-50 transition-colors">
                        <span className="text-sm text-ink">Çalışma Hatırlatıcıları</span>
                        <input
                          type="checkbox"
                          checked={studyReminders}
                          onChange={(e) => setStudyReminders(e.target.checked)}
                          className="w-4 h-4 rounded border-stone-300 text-sepia focus:ring-sepia"
                        />
                      </label>
                    </div>

                    <div className="flex justify-end pt-4 border-t border-stone-200">
                      <Button onClick={handleSavePreferences} isLoading={isLoading}>
                        Kaydet
                      </Button>
                    </div>
                  </div>
                </Card>
              )}

              {/* Subscription Tab */}
              {activeTab === 'subscription' && (
                <Card variant="surface" className="animate-enter">
                  <h2 className="font-serif-custom text-xl italic text-sepia mb-6">
                    Abonelik
                  </h2>

                  <div className="space-y-6">
                    {/* Current Plan */}
                    <div className="p-4 rounded-xl border-2 border-sepia/20 bg-sepia/5">
                      <div className="flex items-center justify-between mb-3">
                        <span className="font-mono-custom text-xs uppercase tracking-wider text-sepia">
                          Mevcut Plan
                        </span>
                        <span className="px-2 py-1 bg-sepia text-paper text-[10px] font-mono-custom uppercase rounded">
                          Aktif
                        </span>
                      </div>
                      <h3 className="font-serif-custom text-2xl text-ink mb-1">Ücretsiz</h3>
                      <p className="text-sm text-neutral-600">10 soru/gün</p>
                    </div>

                    {/* Usage */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-neutral-600">Günlük Kullanım</span>
                        <span className="font-mono-custom text-sm text-sepia">7/10</span>
                      </div>
                      <div className="h-2 bg-stone-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-sepia to-accent rounded-full"
                          style={{ width: '70%' }}
                        />
                      </div>
                    </div>

                    {/* Upgrade CTA */}
                    <div className="p-6 rounded-xl bg-gradient-to-br from-sepia/10 to-accent/10 text-center">
                      <h3 className="font-serif-custom text-lg text-ink mb-2">
                        Sınırsız Erişim
                      </h3>
                      <p className="text-sm text-neutral-600 mb-4">
                        Öğrenci planına yükselterek sınırsız soru sorabilirsiniz.
                      </p>
                      <Button>Planı Yükselt - 29 TL/ay</Button>
                    </div>
                  </div>
                </Card>
              )}

              {/* Security Tab */}
              {activeTab === 'security' && (
                <Card variant="surface" className="animate-enter">
                  <h2 className="font-serif-custom text-xl italic text-sepia mb-6">
                    Güvenlik
                  </h2>

                  <div className="space-y-6">
                    <h3 className="font-sans font-medium text-ink">Şifre Değiştir</h3>

                    <Input
                      label="Mevcut Şifre"
                      type="password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      leftIcon={<Lock className="w-4 h-4" />}
                    />

                    <Input
                      label="Yeni Şifre"
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      leftIcon={<Lock className="w-4 h-4" />}
                      hint="En az 8 karakter"
                    />

                    <Input
                      label="Yeni Şifre Tekrar"
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      leftIcon={<Lock className="w-4 h-4" />}
                    />

                    <div className="flex justify-end pt-4 border-t border-stone-200">
                      <Button onClick={handleChangePassword} isLoading={isLoading}>
                        Şifreyi Güncelle
                      </Button>
                    </div>

                    {/* Connected Accounts */}
                    <div className="pt-6 border-t border-stone-200">
                      <h3 className="font-sans font-medium text-ink mb-4">Bağlı Hesaplar</h3>
                      <div className="p-4 rounded-xl border border-stone-200 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <svg className="w-5 h-5" viewBox="0 0 24 24">
                            <path
                              fill="#4285F4"
                              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                            />
                            <path
                              fill="#34A853"
                              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                            />
                            <path
                              fill="#FBBC05"
                              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                            />
                            <path
                              fill="#EA4335"
                              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                            />
                          </svg>
                          <span className="text-sm text-ink">Google</span>
                        </div>
                        <span className="text-xs text-neutral-500">Bağlı değil</span>
                      </div>
                    </div>

                    {/* Danger Zone */}
                    <div className="pt-6 border-t border-stone-200">
                      <h3 className="font-sans font-medium text-red-600 mb-4">Tehlikeli Bölge</h3>
                      <Button variant="danger" onClick={logout}>
                        Çıkış Yap
                      </Button>
                    </div>
                  </div>
                </Card>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Settings;
