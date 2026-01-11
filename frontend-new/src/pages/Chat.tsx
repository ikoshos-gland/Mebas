import { useState, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Send,
  Paperclip,
  Image as ImageIcon,
  X,
  Loader2,
  Sparkles,
  Target,
  BookOpen,
  GraduationCap,
  ThumbsUp,
  ThumbsDown,
  Brain,
  Settings,
  Info,
} from 'lucide-react';
import { ParticleBackground } from '../components/background/ParticleBackground';
import { Header } from '../components/layout/Header';
import { Card } from '../components/common';
import { useAuth } from '../context/AuthContext';
import { grades, subjects, examModes, API_BASE_URL } from '../utils/theme';

// Mock message type
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  image?: string;
  analysis?: {
    kazanimlar: Array<{ code: string; description: string; score: number }>;
    textbookRefs: Array<{ chapter: string; pages: string }>;
    confidence: number;
    processingTime: number;
  };
}

const Chat = () => {
  const { id: _conversationId } = useParams(); // Will be used for loading conversations
  const { user } = useAuth();

  // State
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [currentImage, setCurrentImage] = useState<string | null>(null);
  const [currentImageName, setCurrentImageName] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showSettings] = useState(true); // Will add toggle later

  // Settings - stored in localStorage for persistence
  const [grade, setGrade] = useState(() => {
    const saved = localStorage.getItem('meba_grade');
    return saved ? Number(saved) : (user?.grade || 9);
  });
  const [subject, setSubject] = useState(() => {
    return localStorage.getItem('meba_subject') || 'Biyoloji';
  });
  const [isExamMode, setIsExamMode] = useState(() => {
    return localStorage.getItem('meba_exam_mode') === 'true';
  });
  const [showMobileSettings, setShowMobileSettings] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  // Persist settings to localStorage
  useEffect(() => {
    localStorage.setItem('meba_grade', String(grade));
  }, [grade]);

  useEffect(() => {
    localStorage.setItem('meba_subject', subject);
  }, [subject]);

  useEffect(() => {
    localStorage.setItem('meba_exam_mode', String(isExamMode));
  }, [isExamMode]);

  // Refs
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  // Auto-resize textarea
  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputText(e.target.value);
    e.target.style.height = '';
    e.target.style.height = `${e.target.scrollHeight}px`;
  };

  // Handle file upload
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      alert('Dosya çok büyük (Maks 10MB)');
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      setCurrentImage(event.target?.result as string);
      setCurrentImageName(file.name);
    };
    reader.readAsDataURL(file);
  };

  const clearImage = () => {
    setCurrentImage(null);
    setCurrentImageName(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Handle drag and drop
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Only set dragging to false if we're leaving the drop zone entirely
    if (e.currentTarget.contains(e.relatedTarget as Node)) return;
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files.length === 0) return;

    const file = files[0];

    // Check if it's an image
    if (!file.type.startsWith('image/')) {
      alert('Sadece görsel dosyaları yükleyebilirsiniz');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      alert('Dosya çok büyük (Maks 10MB)');
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      setCurrentImage(event.target?.result as string);
      setCurrentImageName(file.name);
    };
    reader.readAsDataURL(file);
  };

  // Handle send message - calls real API with settings
  const handleSend = async () => {
    if (isLoading || (!inputText.trim() && !currentImage)) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputText,
      image: currentImage || undefined,
    };

    setMessages((prev) => [...prev, userMessage]);
    const questionText = inputText;
    const questionImage = currentImage;
    setInputText('');
    clearImage();
    setIsLoading(true);

    try {
      // Determine which endpoint to use based on whether there's an image
      const endpoint = questionImage
        ? `${API_BASE_URL}/analyze/image`
        : `${API_BASE_URL}/analyze/text`;

      // Build request body with settings
      const requestBody = questionImage
        ? {
            image_base64: questionImage,
            question_text: questionText || undefined,
            grade,
            subject,
            is_exam_mode: isExamMode,
          }
        : {
            question_text: questionText,
            grade,
            subject,
            is_exam_mode: isExamMode,
          };

      console.log('Sending request to:', endpoint, { grade, subject, isExamMode });

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();

      // Transform API response to message format
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.explanation || data.response || 'Yanıt alınamadı.',
        analysis: {
          kazanimlar: (data.matched_kazanimlar || []).map((k: { kazanim_code: string; kazanim_description: string; score: number }) => ({
            code: k.kazanim_code,
            description: k.kazanim_description,
            score: k.score,
          })),
          textbookRefs: (data.related_chunks || []).map((c: { hierarchy_path: string; page_range: string }) => ({
            chapter: c.hierarchy_path,
            pages: c.page_range,
          })),
          confidence: data.confidence || 0.85,
          processingTime: data.processing_time || 0,
        },
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('API Error:', error);
      // Fallback to mock response on error
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.\n\n*Hata: ${error instanceof Error ? error.message : 'Bilinmeyen hata'}*`,
        analysis: undefined,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle keyboard submit
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="h-screen w-screen overflow-hidden relative bg-canvas">
      <ParticleBackground />

      {/* Header */}
      <Header transparent />

      {/* Main Content */}
      <main
        className="relative z-20 h-full w-full flex flex-col pt-24"
        onDragOver={handleDragOver}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* Full-screen drag overlay */}
        {isDragging && (
          <div className="fixed inset-0 z-50 bg-canvas/80 backdrop-blur-sm flex items-center justify-center pointer-events-none">
            <div className="bg-paper rounded-2xl p-8 shadow-2xl border-2 border-dashed border-sepia flex flex-col items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-sepia/10 flex items-center justify-center">
                <ImageIcon className="w-8 h-8 text-sepia" />
              </div>
              <div className="text-center">
                <p className="text-lg font-medium text-ink">Görseli buraya bırakın</p>
                <p className="text-sm text-neutral-500 mt-1">PNG, JPG, WEBP (maks 10MB)</p>
              </div>
            </div>
          </div>
        )}

        {/* Chat Stream */}
        <div
          ref={chatContainerRef}
          className="flex-1 overflow-y-auto w-full scroll-smooth"
        >
          <div className="max-w-3xl mx-auto px-4 md:px-6 w-full pb-48 pt-10 flex flex-col gap-12">
            {/* Welcome State */}
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center min-h-[35vh] opacity-90 animate-enter">
                <div className="p-10 rounded-full glass-vellum flex flex-col items-center text-center shadow-2xl ring-1 ring-white/60">
                  <Brain className="w-12 h-12 text-ink mb-4 stroke-[1]" />
                  <p className="font-serif-custom text-4xl italic text-ink tracking-tight">
                    Meba AI
                  </p>
                  <p className="font-mono-custom text-[10px] text-neutral-500 mt-3 tracking-widest uppercase">
                    Kişiselleştirilmiş Öğrenci Eğitim Sohbet Motoru
                  </p>
                </div>
              </div>
            )}

            {/* Messages */}
            {messages.map((message) => (
              <div key={message.id} className="animate-enter">
                {message.role === 'user' ? (
                  // User Message
                  <div className="flex justify-end">
                    <div className="card-surface max-w-2xl px-6 py-5 rounded-2xl rounded-tr-sm shadow-sm">
                      <p className="font-sans text-sm md:text-base font-light leading-relaxed text-ink whitespace-pre-wrap">
                        {message.content}
                      </p>
                      {message.image && (
                        <div className="mt-4 flex items-center gap-3 px-3 py-2 bg-stone-50 rounded border border-stone-200 w-fit">
                          <div className="bg-white p-1 rounded border border-stone-200">
                            <ImageIcon className="w-3 h-3 text-sepia" />
                          </div>
                          <span className="font-mono-custom text-[10px] text-neutral-600">
                            Görsel eklendi
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  // Assistant Message
                  <div className="flex gap-5 w-full">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-ink to-neutral-600 flex items-center justify-center flex-shrink-0 mt-1 shadow-lg ring-2 ring-paper">
                      <Sparkles className="w-3.5 h-3.5 text-paper" />
                    </div>

                    <div className="flex flex-col gap-4 w-full">
                      <Card variant="surface" padding="lg" className="rounded-tl-sm">
                        {/* Header */}
                        <div className="flex items-center justify-between mb-4 pb-4 border-b border-stone-200">
                          <span className="font-serif-custom text-lg italic text-sepia">
                            Analiz Sonucu
                          </span>
                          {message.analysis && (
                            <div className="flex items-center gap-2">
                              <span className="font-mono-custom text-[9px] text-neutral-400 bg-stone-50 px-2 py-1 rounded border border-stone-200/50">
                                GÜVEN: {Math.round(message.analysis.confidence * 100)}%
                              </span>
                              <span className="font-mono-custom text-[9px] text-neutral-400 bg-stone-50 px-2 py-1 rounded border border-stone-200/50">
                                SÜRE: {message.analysis.processingTime}s
                              </span>
                            </div>
                          )}
                        </div>

                        {/* Teacher Explanation */}
                        <div className="mb-6 bg-gradient-to-br from-sepia/5 to-accent/5 rounded-xl p-5 border border-sepia/20">
                          <div className="flex items-center gap-3 mb-4">
                            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-sepia to-accent flex items-center justify-center shadow-lg">
                              <GraduationCap className="w-5 h-5 text-white" />
                            </div>
                            <div>
                              <span className="font-serif-custom text-base font-medium text-sepia">
                                Öğretmen Açıklaması
                              </span>
                              <span className="text-xs text-neutral-400 ml-2 font-mono-custom">
                                GPT-5.2
                              </span>
                            </div>
                          </div>
                          <div className="prose prose-sm max-w-none font-sans leading-7 text-ink/90 whitespace-pre-wrap">
                            {message.content}
                          </div>
                        </div>

                        {/* Kazanımlar */}
                        {message.analysis?.kazanimlar && message.analysis.kazanimlar.length > 0 && (
                          <div className="mb-6">
                            <h3 className="font-serif-custom text-base italic text-sepia mb-3 flex items-center gap-2">
                              <Target className="w-4 h-4" />
                              Eşleşen Kazanımlar
                            </h3>
                            <div className="space-y-3">
                              {message.analysis.kazanimlar.map((k) => (
                                <div
                                  key={k.code}
                                  className="bg-stone-50/60 rounded-lg p-4 border border-stone-200"
                                >
                                  <div className="flex items-start justify-between gap-3 mb-2">
                                    <span className="font-mono-custom text-xs font-semibold text-sepia bg-sepia/10 px-2 py-1 rounded">
                                      {k.code}
                                    </span>
                                    <span className="font-mono-custom text-[10px] text-neutral-400">
                                      %{Math.round(k.score * 100)}
                                    </span>
                                  </div>
                                  <p className="text-sm text-ink/80 leading-relaxed">
                                    {k.description}
                                  </p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Textbook References */}
                        {message.analysis?.textbookRefs && message.analysis.textbookRefs.length > 0 && (
                          <div className="mb-6">
                            <h3 className="font-serif-custom text-base italic text-sepia mb-3 flex items-center gap-2">
                              <BookOpen className="w-4 h-4" />
                              Ders Kitabı Referansları
                            </h3>
                            <div className="space-y-2">
                              {message.analysis.textbookRefs.map((ref, i) => (
                                <div
                                  key={i}
                                  className="bg-white rounded-lg p-3 border border-stone-200"
                                >
                                  <div className="flex items-center justify-between">
                                    <span className="font-mono-custom text-xs font-medium text-ink">
                                      {ref.chapter}
                                    </span>
                                    <span className="font-mono-custom text-[10px] text-sepia bg-sepia/5 px-2 py-0.5 rounded">
                                      Sayfa {ref.pages}
                                    </span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Actions */}
                        <div className="flex items-center gap-3 pt-4 border-t border-stone-200/60">
                          <span className="font-mono-custom text-[10px] text-neutral-400">
                            {message.analysis?.kazanimlar?.length || 0} kazanım eşleşti
                          </span>
                          <div className="flex-grow" />
                          <button className="p-1.5 hover:bg-stone-50 rounded text-neutral-400 hover:text-ink transition-colors">
                            <ThumbsUp className="w-3.5 h-3.5" />
                          </button>
                          <button className="p-1.5 hover:bg-stone-50 rounded text-neutral-400 hover:text-ink transition-colors">
                            <ThumbsDown className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </Card>
                    </div>
                  </div>
                )}
              </div>
            ))}

            {/* Loading State */}
            {isLoading && (
              <div className="flex gap-5 animate-enter">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-ink to-neutral-600 flex items-center justify-center flex-shrink-0 mt-1 shadow-lg ring-2 ring-paper">
                  <Loader2 className="w-3.5 h-3.5 text-paper animate-spin" />
                </div>
                <Card variant="surface" padding="lg" className="flex-1">
                  <div className="animate-pulse space-y-3">
                    <div className="h-2 bg-stone-200 rounded w-3/4" />
                    <div className="h-2 bg-stone-200 rounded w-1/2" />
                  </div>
                </Card>
              </div>
            )}
          </div>
        </div>

        {/* Input Area */}
        <div className="absolute bottom-0 left-0 right-0 z-40 bg-gradient-to-t from-canvas via-canvas/80 to-transparent pt-12 pb-8 md:pb-10">
          <div className="max-w-3xl mx-auto px-4 md:px-6">
            <div className="glass-input rounded-2xl p-2 pl-4 flex items-end gap-3 transition-all focus-within:ring-1 focus-within:ring-ink/10 relative overflow-hidden">
              <div className="absolute bottom-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-sepia/30 to-transparent opacity-50" />

              {/* Upload Button */}
              <div className="flex pb-2 gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={handleFileSelect}
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className={`p-2 rounded-lg hover:bg-ink/5 transition-colors ${
                    currentImage ? 'bg-sepia/10 text-sepia' : 'text-neutral-400 hover:text-ink'
                  }`}
                  title="Görsel Yükle"
                >
                  <Paperclip className="w-5 h-5 stroke-[1.5]" />
                </button>
              </div>

              {/* Image Preview */}
              {currentImage && (
                <div className="flex-shrink-0 pb-2">
                  <div className="flex items-center gap-2 px-3 py-2 bg-stone-50 rounded-lg border border-stone-200">
                    <div className="bg-white p-1.5 rounded border border-stone-200">
                      <ImageIcon className="w-4 h-4 text-sepia" />
                    </div>
                    <span className="font-mono-custom text-xs text-neutral-600 max-w-[150px] truncate">
                      {currentImageName}
                    </span>
                    <button
                      type="button"
                      onClick={clearImage}
                      className="p-1 hover:bg-neutral-200 rounded transition-colors"
                    >
                      <X className="w-3 h-3 text-neutral-500" />
                    </button>
                  </div>
                </div>
              )}

              {/* Textarea */}
              <textarea
                ref={textareaRef}
                rows={1}
                value={inputText}
                onChange={handleTextareaChange}
                onKeyDown={handleKeyDown}
                placeholder="Sorunuzu yazın..."
                className="w-full bg-transparent border-0 focus:ring-0 p-3 pb-3 font-sans text-base font-light text-ink placeholder:text-neutral-400 resize-none max-h-32 leading-relaxed"
              />

              {/* Send Button */}
              <button
                onClick={handleSend}
                disabled={isLoading || (!inputText.trim() && !currentImage)}
                className="mb-1 p-2.5 bg-ink text-paper rounded-xl hover:bg-sepia transition-all shadow-md active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5 stroke-[1.5]" />
                )}
              </button>
            </div>

            <div className="text-center mt-3">
              <span className="font-mono-custom text-[9px] text-neutral-500 tracking-widest uppercase flex items-center justify-center gap-2">
                <span className="w-1 h-1 rounded-full bg-green-500" />
                MEB müfredatına uyumlu yanıtlar
              </span>
            </div>
          </div>
        </div>
      </main>

      {/* Mobile Settings Button */}
      <button
        onClick={() => setShowMobileSettings(!showMobileSettings)}
        className="fixed bottom-32 right-4 xl:hidden z-50 p-3 bg-ink text-paper rounded-full shadow-lg hover:bg-sepia transition-colors"
        title="Ayarlar"
      >
        <Settings className="w-5 h-5" />
      </button>

      {/* Settings Panel (Desktop + Mobile) */}
      {(showSettings || showMobileSettings) && (
        <div className={`
          ${showMobileSettings ? 'fixed inset-x-4 bottom-36 xl:absolute xl:inset-auto' : 'absolute hidden xl:block'}
          xl:top-24 xl:right-6 w-auto xl:w-72 card-surface rounded-xl z-40 animate-enter shadow-xl
        `}>
          {/* Header */}
          <div className="border-b border-stone-200 px-4 py-3 flex justify-between items-center bg-stone-50/50 rounded-t-xl">
            <span className="font-serif-custom italic text-base text-ink flex items-center gap-2">
              <Settings className="w-4 h-4" />
              Kalibrasyon
            </span>
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-green-500/80 shadow-[0_0_8px_rgba(34,197,94,0.4)]" />
              {showMobileSettings && (
                <button
                  onClick={() => setShowMobileSettings(false)}
                  className="xl:hidden p-1 hover:bg-stone-100 rounded"
                >
                  <X className="w-4 h-4 text-neutral-500" />
                </button>
              )}
            </div>
          </div>

          <div className="p-4 space-y-5">
            {/* Grade Selection with grouped options */}
            <div className="space-y-2">
              <label className="font-mono-custom text-[10px] tracking-widest text-neutral-500 uppercase flex items-center gap-1">
                <GraduationCap className="w-3 h-3" />
                Sınıf Seviyesi
              </label>
              <select
                value={grade}
                onChange={(e) => setGrade(Number(e.target.value))}
                className="w-full appearance-none bg-paper border border-stone-200 text-ink text-sm font-sans p-2.5 rounded-lg hover:border-ink/30 focus:outline-none focus:border-sepia focus:ring-1 focus:ring-sepia/20 transition-colors cursor-pointer shadow-sm"
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

            {/* Subject Selection */}
            <div className="space-y-2">
              <label className="font-mono-custom text-[10px] tracking-widest text-neutral-500 uppercase flex items-center gap-1">
                <BookOpen className="w-3 h-3" />
                Ders
              </label>
              <select
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full appearance-none bg-paper border border-stone-200 text-ink text-sm font-sans p-2.5 rounded-lg hover:border-ink/30 focus:outline-none focus:border-sepia focus:ring-1 focus:ring-sepia/20 transition-colors cursor-pointer shadow-sm"
              >
                {subjects.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.icon} {s.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Exam Mode Toggle with Description */}
            <div className="space-y-3 pt-3 border-t border-stone-200">
              <div className="flex items-center justify-between">
                <span className="font-mono-custom text-[10px] tracking-widest text-neutral-500 uppercase flex items-center gap-1">
                  {isExamMode ? examModes.yks.icon : examModes.school.icon}
                  {isExamMode ? 'YKS Modu' : 'Okul Modu'}
                </span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isExamMode}
                    onChange={(e) => setIsExamMode(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-stone-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-sepia/20 rounded-full peer peer-checked:bg-sepia transition-colors">
                    <span className="absolute top-[2px] left-[2px] bg-paper border border-stone-300 h-5 w-5 rounded-full transition-transform duration-300 peer-checked:translate-x-5 shadow-sm" />
                  </div>
                </label>
              </div>
              {/* Mode description */}
              <div className={`flex items-start gap-2 p-2.5 rounded-lg text-xs ${
                isExamMode ? 'bg-sepia/10 text-sepia' : 'bg-stone-100 text-neutral-600'
              }`}>
                <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                <span className="leading-relaxed">
                  {isExamMode
                    ? examModes.yks.description
                    : examModes.school.description
                  }
                </span>
              </div>
            </div>

            {/* Current Settings Summary */}
            <div className="pt-3 border-t border-stone-200">
              <div className="bg-stone-50 rounded-lg p-3 space-y-1.5">
                <div className="flex justify-between text-[10px] font-mono-custom">
                  <span className="text-neutral-400">Aktif Filtre</span>
                  <span className="text-ink font-medium">
                    {grades.find(g => g.value === grade)?.label} • {subject}
                  </span>
                </div>
                <div className="flex justify-between text-[10px] font-mono-custom">
                  <span className="text-neutral-400">İçerik Kapsamı</span>
                  <span className={`font-medium ${isExamMode ? 'text-sepia' : 'text-ink'}`}>
                    {isExamMode ? `1-${grade}. Sınıf` : `Sadece ${grade}. Sınıf`}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Mobile Settings Overlay */}
      {showMobileSettings && (
        <div
          className="fixed inset-0 bg-black/20 z-30 xl:hidden"
          onClick={() => setShowMobileSettings(false)}
        />
      )}
    </div>
  );
};

export default Chat;
