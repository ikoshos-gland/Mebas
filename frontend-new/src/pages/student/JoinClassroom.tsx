/**
 * Join Classroom Page
 * Students can enter a join code to enroll in a classroom
 */
import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../../services/api';

interface JoinResponse {
  classroom_id: number;
  classroom_name: string;
  teacher_name: string;
  grade: number;
  subject: string | null;
}

const JoinClassroom = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialCode = searchParams.get('code') || '';

  const [joinCode, setJoinCode] = useState(initialCode);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<JoinResponse | null>(null);

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const code = joinCode.trim().toUpperCase();
    if (code.length !== 8) {
      setError('Katilim kodu 8 karakter olmali');
      return;
    }

    try {
      setIsLoading(true);
      const response = await api.post<JoinResponse>('/classrooms/join', { join_code: code });
      setSuccess(response.data);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (detail === 'Invalid join code') {
        setError('Gecersiz katilim kodu');
      } else if (detail === 'Join code is disabled') {
        setError('Bu sinifin katilimi kapatilmis');
      } else if (detail === 'Already enrolled') {
        setError('Bu sinifa zaten kayitlisiniz');
      } else {
        setError(detail || 'Sinifa katilirken hata olustu');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleCodeChange = (value: string) => {
    // Only allow alphanumeric, convert to uppercase, max 8 chars
    const cleaned = value.replace(/[^A-Za-z0-9]/g, '').toUpperCase().slice(0, 8);
    setJoinCode(cleaned);
  };

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center px-4">
        <div className="max-w-md w-full">
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-8 text-center">
            <div className="w-16 h-16 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-8 h-8 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Basariyla Katildiniz!</h2>
            <p className="text-slate-400 mb-6">
              {success.classroom_name} sinifina kayit oldunuz
            </p>
            <div className="bg-slate-700/50 rounded-lg p-4 mb-6 text-left">
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">Sinif</span>
                  <span className="text-white">{success.classroom_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Ogretmen</span>
                  <span className="text-white">{success.teacher_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Seviye</span>
                  <span className="text-white">{success.grade}. Sinif</span>
                </div>
                {success.subject && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Ders</span>
                    <span className="text-white">{success.subject}</span>
                  </div>
                )}
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => navigate('/siniflarim')}
                className="flex-1 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
              >
                Siniflarima Git
              </button>
              <button
                onClick={() => { setSuccess(null); setJoinCode(''); }}
                className="px-4 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium transition-colors"
              >
                Baska Sinif
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white">Sinifa Katil</h1>
          <p className="text-slate-400 mt-2">
            Ogretmeninizden aldiginiz katilim kodunu girin
          </p>
        </div>

        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-8">
          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleJoin}>
            <div className="mb-6">
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Katilim Kodu
              </label>
              <input
                type="text"
                value={joinCode}
                onChange={(e) => handleCodeChange(e.target.value)}
                placeholder="ABCD1234"
                className="w-full px-4 py-4 bg-slate-700 border border-slate-600 rounded-lg text-white text-center text-2xl font-mono tracking-widest placeholder-slate-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none uppercase"
                autoFocus
                autoComplete="off"
              />
              <p className="text-xs text-slate-500 mt-2 text-center">
                8 karakterlik kod (harf ve rakam)
              </p>
            </div>

            <button
              type="submit"
              disabled={isLoading || joinCode.length !== 8}
              className="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  Katiliniyor...
                </span>
              ) : (
                'Sinifa Katil'
              )}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-slate-700 text-center">
            <button
              onClick={() => navigate('/panel')}
              className="text-slate-400 hover:text-white text-sm"
            >
              Panele Don
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default JoinClassroom;
