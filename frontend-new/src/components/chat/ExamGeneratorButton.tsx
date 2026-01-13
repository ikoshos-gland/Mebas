/**
 * ExamGeneratorButton Component
 *
 * Button to trigger exam PDF generation based on user's tracked kazanimlar.
 */
import { useState } from 'react';
import { FileText, Download, X, CheckCircle, AlertCircle } from 'lucide-react';
import { Button } from '../common/Button';
import { Modal } from '../common/Modal';
import { useExamGenerator } from '../../hooks/useExamGenerator';
import { useProgress } from '../../hooks/useProgress';
import type { ExamGenerateRequest } from '../../types';

interface ExamGeneratorButtonProps {
  className?: string;
}

export const ExamGeneratorButton = ({ className = '' }: ExamGeneratorButtonProps) => {
  const { trackedCount } = useProgress();
  const {
    isGenerating,
    error,
    lastGeneratedExam,
    generateExam,
    downloadExam,
    clearError,
  } = useExamGenerator();

  const [showModal, setShowModal] = useState(false);
  const [questionCount, setQuestionCount] = useState(10);
  const [title, setTitle] = useState('Calisma Sinavi');
  const [showSuccess, setShowSuccess] = useState(false);

  // Zorluk dağılımı (yüzde olarak, toplam 100 olmalı)
  const [difficultyKolay, setDifficultyKolay] = useState(30);
  const [difficultyOrta, setDifficultyOrta] = useState(50);
  const [difficultyZor, setDifficultyZor] = useState(20);

  const hasKazanimlar = trackedCount > 0;

  const handleOpenModal = () => {
    clearError();
    setShowSuccess(false);
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setShowSuccess(false);
  };

  const handleGenerate = async () => {
    const options: ExamGenerateRequest = {
      title,
      question_count: questionCount,
      difficulty_distribution: {
        kolay: difficultyKolay / 100,
        orta: difficultyOrta / 100,
        zor: difficultyZor / 100,
      },
    };

    const result = await generateExam(options);

    if (result) {
      setShowSuccess(true);
    }
  };

  // Zorluk değişikliğinde diğerlerini otomatik ayarla
  const handleDifficultyChange = (
    type: 'kolay' | 'orta' | 'zor',
    value: number
  ) => {
    const newValue = Math.max(0, Math.min(100, value));

    if (type === 'kolay') {
      const remaining = 100 - newValue;
      const ratio = difficultyOrta + difficultyZor > 0
        ? remaining / (difficultyOrta + difficultyZor)
        : 0.5;
      setDifficultyKolay(newValue);
      if (difficultyOrta + difficultyZor > 0) {
        setDifficultyOrta(Math.round(difficultyOrta * ratio));
        setDifficultyZor(100 - newValue - Math.round(difficultyOrta * ratio));
      } else {
        setDifficultyOrta(Math.round(remaining * 0.7));
        setDifficultyZor(remaining - Math.round(remaining * 0.7));
      }
    } else if (type === 'orta') {
      const remaining = 100 - newValue;
      const ratio = difficultyKolay + difficultyZor > 0
        ? remaining / (difficultyKolay + difficultyZor)
        : 0.5;
      setDifficultyOrta(newValue);
      if (difficultyKolay + difficultyZor > 0) {
        setDifficultyKolay(Math.round(difficultyKolay * ratio));
        setDifficultyZor(100 - newValue - Math.round(difficultyKolay * ratio));
      } else {
        setDifficultyKolay(Math.round(remaining * 0.6));
        setDifficultyZor(remaining - Math.round(remaining * 0.6));
      }
    } else {
      const remaining = 100 - newValue;
      const ratio = difficultyKolay + difficultyOrta > 0
        ? remaining / (difficultyKolay + difficultyOrta)
        : 0.5;
      setDifficultyZor(newValue);
      if (difficultyKolay + difficultyOrta > 0) {
        setDifficultyKolay(Math.round(difficultyKolay * ratio));
        setDifficultyOrta(100 - newValue - Math.round(difficultyKolay * ratio));
      } else {
        setDifficultyKolay(Math.round(remaining * 0.4));
        setDifficultyOrta(remaining - Math.round(remaining * 0.4));
      }
    }
  };

  const handleDownload = () => {
    if (lastGeneratedExam) {
      downloadExam(lastGeneratedExam.exam_id);
    }
  };

  return (
    <>
      {/* Main Button */}
      <Button
        onClick={handleOpenModal}
        disabled={!hasKazanimlar}
        variant="secondary"
        size="md"
        leftIcon={<FileText className="w-4 h-4" />}
        className={className}
        title={!hasKazanimlar ? 'Sinav olusturmak icin once kazanim biriktirin' : ''}
      >
        Sinav Hazirla
      </Button>

      {/* Modal */}
      <Modal isOpen={showModal} onClose={handleCloseModal}>
        <div className="p-6 max-w-md mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-ink">Sinav Olustur</h2>
            <button
              onClick={handleCloseModal}
              className="p-1 hover:bg-stone-100 rounded-full transition-colors"
            >
              <X className="w-5 h-5 text-neutral-500" />
            </button>
          </div>

          {/* Success State */}
          {showSuccess && lastGeneratedExam ? (
            <div className="text-center py-6">
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-ink mb-2">
                Sinav Hazirlandi!
              </h3>
              <p className="text-neutral-600 mb-4">
                {lastGeneratedExam.question_count} soru ile sinav olusturuldu.
              </p>

              {/* Uyarı mesajı - bazı kazanımlar atlandıysa */}
              {lastGeneratedExam.warning && (
                <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-left">
                  <p className="text-sm text-amber-800">
                    <AlertCircle className="w-4 h-4 inline-block mr-1" />
                    {lastGeneratedExam.warning}
                  </p>
                  {lastGeneratedExam.skipped_kazanimlar && lastGeneratedExam.skipped_kazanimlar.length > 0 && (
                    <p className="text-xs text-amber-600 mt-1">
                      Atlanan: {lastGeneratedExam.skipped_kazanimlar.slice(0, 3).join(', ')}
                      {lastGeneratedExam.skipped_kazanimlar.length > 3 && '...'}
                    </p>
                  )}
                </div>
              )}

              <div className="flex gap-3 justify-center">
                <Button
                  onClick={handleDownload}
                  variant="primary"
                  leftIcon={<Download className="w-4 h-4" />}
                >
                  PDF Indir
                </Button>
                <Button onClick={handleCloseModal} variant="ghost">
                  Kapat
                </Button>
              </div>
            </div>
          ) : (
            <>
              {/* Error State */}
              {error && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              {/* Info */}
              <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <p className="text-sm text-amber-800">
                  <strong>{trackedCount}</strong> kazanim takip ediyorsunuz.
                  Bu kazanimlara gore soru secimi yapilacak.
                </p>
              </div>

              {/* Form */}
              <div className="space-y-4 mb-6">
                {/* Title */}
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">
                    Sinav Basligi
                  </label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sepia/50"
                    placeholder="Calisma Sinavi"
                  />
                </div>

                {/* Question Count */}
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">
                    Soru Sayisi: <span className="font-bold">{questionCount}</span>
                  </label>
                  <input
                    type="range"
                    min={5}
                    max={30}
                    value={questionCount}
                    onChange={(e) => setQuestionCount(Number(e.target.value))}
                    className="w-full accent-sepia"
                  />
                  <div className="flex justify-between text-xs text-neutral-500">
                    <span>5</span>
                    <span>30</span>
                  </div>
                </div>

                {/* Difficulty Distribution Sliders */}
                <div className="text-sm text-neutral-600">
                  <p className="font-medium mb-3">Zorluk Dagilimi:</p>

                  {/* Kolay */}
                  <div className="mb-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-green-400"></span>
                        Kolay
                      </span>
                      <span className="font-bold text-green-600">%{difficultyKolay}</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={100}
                      value={difficultyKolay}
                      onChange={(e) => handleDifficultyChange('kolay', Number(e.target.value))}
                      className="w-full h-2 rounded-lg appearance-none cursor-pointer accent-green-500"
                      style={{ background: `linear-gradient(to right, #22c55e ${difficultyKolay}%, #e5e7eb ${difficultyKolay}%)` }}
                    />
                  </div>

                  {/* Orta */}
                  <div className="mb-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-blue-400"></span>
                        Orta
                      </span>
                      <span className="font-bold text-blue-600">%{difficultyOrta}</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={100}
                      value={difficultyOrta}
                      onChange={(e) => handleDifficultyChange('orta', Number(e.target.value))}
                      className="w-full h-2 rounded-lg appearance-none cursor-pointer accent-blue-500"
                      style={{ background: `linear-gradient(to right, #3b82f6 ${difficultyOrta}%, #e5e7eb ${difficultyOrta}%)` }}
                    />
                  </div>

                  {/* Zor */}
                  <div className="mb-2">
                    <div className="flex items-center justify-between mb-1">
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-red-400"></span>
                        Zor
                      </span>
                      <span className="font-bold text-red-600">%{difficultyZor}</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={100}
                      value={difficultyZor}
                      onChange={(e) => handleDifficultyChange('zor', Number(e.target.value))}
                      className="w-full h-2 rounded-lg appearance-none cursor-pointer accent-red-500"
                      style={{ background: `linear-gradient(to right, #ef4444 ${difficultyZor}%, #e5e7eb ${difficultyZor}%)` }}
                    />
                  </div>

                  {/* Toplam göstergesi */}
                  <div className="flex justify-center mt-2">
                    <div className="flex gap-1 h-3 w-full rounded-full overflow-hidden border border-stone-200">
                      <div
                        className="bg-green-400 transition-all"
                        style={{ width: `${difficultyKolay}%` }}
                      />
                      <div
                        className="bg-blue-400 transition-all"
                        style={{ width: `${difficultyOrta}%` }}
                      />
                      <div
                        className="bg-red-400 transition-all"
                        style={{ width: `${difficultyZor}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3">
                <Button
                  onClick={handleGenerate}
                  variant="primary"
                  isLoading={isGenerating}
                  leftIcon={isGenerating ? undefined : <FileText className="w-4 h-4" />}
                  className="flex-1"
                >
                  {isGenerating ? 'Hazirlaniyor...' : 'Sinav Olustur'}
                </Button>
                <Button onClick={handleCloseModal} variant="ghost">
                  Iptal
                </Button>
              </div>
            </>
          )}
        </div>
      </Modal>
    </>
  );
};

export default ExamGeneratorButton;
