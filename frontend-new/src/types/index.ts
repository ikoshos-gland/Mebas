/**
 * Yediiklim AI Asistan Application Types
 */

// User Types
export interface User {
  id: number;
  firebase_uid: string;
  email: string;
  full_name: string;
  role: 'student' | 'teacher' | 'admin';
  grade?: number;
  avatar_url?: string;
  is_verified: boolean;
  profile_complete: boolean;
  created_at: string;
}

export interface UserPreferences {
  default_grade?: number;
  default_subject?: string;
  is_exam_mode: boolean;
  language: string;
  email_notifications: boolean;
  study_reminders: boolean;
}

// Auth Types
export interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

export interface LoginCredentials {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface RegisterData {
  email: string;
  password: string;
  full_name: string;
  role: 'student' | 'teacher';
  grade?: number;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// Subscription Types
export interface Subscription {
  id: number;
  plan: 'free' | 'student' | 'school';
  status: 'active' | 'cancelled' | 'expired';
  questions_used_today: number;
  questions_limit: number;
  current_period_end?: string;
}

// Chat Types
export interface Conversation {
  id: string;
  title: string;
  subject?: string;
  grade?: number;
  is_archived?: boolean;
  created_at: string;
  updated_at?: string;
  message_count?: number;
}

export interface ConversationListResponse {
  items: Conversation[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface ConversationMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  image_url?: string;
  analysis_id?: string;
  extra_data?: Record<string, unknown>;
  created_at: string;
}

export interface ConversationWithMessages extends Conversation {
  messages: ConversationMessage[];
}

export interface Message {
  id: number;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  image_url?: string;
  analysis_id?: string;
  created_at: string;
}

// Analysis Types (RAG Response)
export interface KazanimMatch {
  code: string;
  description: string;
  score: number;
  grade?: number;
}

export interface TextbookReference {
  chapter: string;
  pages?: string;
  content?: string;
}

export interface PrerequisiteGap {
  missing_kazanim_description?: string;
  suggestion?: string;
}

export interface SolutionStep {
  step_number: number;
  description: string;
  result?: string;
}

export interface AnalysisResponse {
  analysis_id: string;
  status: 'success' | 'partial' | 'failed';
  summary?: string;
  teacher_explanation?: string;
  matched_kazanimlar: KazanimMatch[];
  prerequisite_gaps: PrerequisiteGap[];
  textbook_references: TextbookReference[];
  solution_steps?: SolutionStep[];
  final_answer?: string;
  study_suggestions?: string[];
  confidence: number;
  processing_time_ms: number;
}

// API Request Types
export interface AnalyzeTextRequest {
  question_text: string;
  grade?: number;
  subject?: string;
  is_exam_mode: boolean;
}

export interface AnalyzeImageRequest {
  image_base64: string;
  grade?: number;
  subject?: string;
  is_exam_mode: boolean;
}

// UI State Types
export interface ChatState {
  thread_id: string;
  grade: number;
  subject: string;
  is_exam_mode: boolean;
  current_image: string | null;
  is_loading: boolean;
  is_streaming: boolean;
}

// SSE Event Types
export interface SSEEvent {
  event: 'rag_complete' | 'teacher_token' | 'done' | 'error';
  data?: AnalysisResponse;
  token?: string;
  error?: string;
}

// Stats Types
export interface UserStats {
  questions_this_week: number;
  topics_covered: number;
  study_streak: number;
  total_questions: number;
}

// ================== PROGRESS TRACKING TYPES ==================

export type KazanimProgressStatus = 'tracked' | 'in_progress' | 'understood';

export interface KazanimProgress {
  kazanim_code: string;
  kazanim_description: string;
  status: KazanimProgressStatus;
  initial_confidence_score: number;
  understanding_confidence?: number;
  tracked_at: string;
  understood_at?: string;
  grade?: number;
  subject?: string;
}

export interface ProgressListResponse {
  items: KazanimProgress[];
  total: number;
  understood_count: number;
  tracked_count: number;
  in_progress_count: number;
}

export interface ProgressStats {
  total_tracked: number;
  total_understood: number;
  in_progress_count: number;
  this_week_understood: number;
  streak_days: number;
  by_subject: Record<string, { tracked: number; in_progress: number; understood: number }>;
  by_grade: Record<number, { tracked: number; in_progress: number; understood: number }>;
}

export type RecommendationPriority = 'critical' | 'important' | 'helpful';

export interface PrerequisiteRecommendation {
  kazanim_code: string;
  kazanim_description: string;
  grade: number;
  reason: string;
  priority: RecommendationPriority;
  related_to: string[];
}

export interface TrackKazanimRequest {
  kazanim_code: string;
  confidence_score: number;
  conversation_id?: string;
}

export interface MarkUnderstoodRequest {
  understanding_signals?: string[];
  understanding_confidence?: number;
}
