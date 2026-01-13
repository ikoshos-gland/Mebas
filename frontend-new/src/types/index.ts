/**
 * Yediiklim AI Asistan Application Types
 */

// User Types
export type UserRole = 'student' | 'teacher' | 'school_admin' | 'platform_admin';

export interface User {
  id: number;
  firebase_uid: string;
  email: string;
  full_name: string;
  role: UserRole;
  grade?: number;
  avatar_url?: string;
  is_verified: boolean;
  profile_complete: boolean;
  school_id?: number;
  school_name?: string;
  created_at: string;
  last_login?: string;
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
  textbookName?: string;
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

// ================== EXAM GENERATOR TYPES ==================

export interface ExamGenerateRequest {
  title?: string;
  question_count?: number;
  difficulty_distribution?: {
    kolay: number;
    orta: number;
    zor: number;
  };
  kazanim_codes?: string[];
}

export interface ExamQuestionDetail {
  file: string;
  kazanim: string;
  difficulty: 'kolay' | 'orta' | 'zor';
  answer?: string;
}

export interface ExamGenerateResponse {
  exam_id: string;
  pdf_url: string;
  kazanimlar_covered: string[];
  question_count: number;
  questions: ExamQuestionDetail[];
  created_at: string;
  skipped_kazanimlar?: string[];
  warning?: string;
}

export interface ExamListItem {
  exam_id: string;
  title: string;
  question_count: number;
  kazanimlar_count: number;
  pdf_url: string;
  created_at: string;
}

export interface ExamListResponse {
  exams: ExamListItem[];
  total: number;
}

export interface AvailableQuestionsStats {
  kazanimlar: Array<{
    code: string;
    available_questions: number;
  }>;
  total_questions: number;
  total_kazanimlar: number;
  message?: string;
}

// ================== SAAS/SCHOOL TYPES ==================

export type SchoolTier = 'small' | 'medium' | 'large';

export interface School {
  id: number;
  name: string;
  slug: string;
  admin_email: string;
  phone?: string;
  address?: string;
  city?: string;
  tier: SchoolTier;
  max_students: number;
  max_teachers: number;
  features: Record<string, boolean>;
  is_active: boolean;
  activated_at?: string;
  expires_at?: string;
  created_at: string;
  updated_at: string;
}

export interface SchoolWithStats extends School {
  student_count: number;
  teacher_count: number;
  classroom_count: number;
}

export interface SchoolListResponse {
  items: SchoolWithStats[];
  total: number;
  page: number;
  page_size: number;
}

export interface TierInfo {
  name: string;
  max_students: number;
  max_teachers: number;
  max_classrooms: number;
  price_try: number;
  features: Record<string, boolean>;
}

// ================== CLASSROOM TYPES ==================

export interface Classroom {
  id: number;
  name: string;
  grade: number;
  subject?: string;
  join_code: string;
  join_enabled: boolean;
  student_count: number;
  is_active: boolean;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  teacher_name?: string;
}

export interface ClassroomListResponse {
  items: Classroom[];
  total: number;
}

export interface CreateClassroomRequest {
  name: string;
  grade: number;
  subject?: string;
}

export interface UpdateClassroomRequest {
  name?: string;
  subject?: string;
  join_enabled?: boolean;
}

// ================== ENROLLMENT TYPES ==================

export type EnrollmentStatus = 'active' | 'inactive' | 'removed';

export interface StudentEnrollment {
  id: number;
  student_id: number;
  student_name: string;
  student_email: string;
  student_grade?: number;
  status: EnrollmentStatus;
  enrolled_at: string;
  removed_at?: string;
}

export interface EnrollmentListResponse {
  items: StudentEnrollment[];
  total: number;
}

export interface EnrolledClassroom {
  id: number;
  classroom_id: number;
  classroom_name: string;
  grade: number;
  subject?: string;
  teacher_name: string;
  enrolled_at: string;
}

// ================== CLASSROOM PROGRESS TYPES ==================

export interface StudentProgressSummary {
  student_id: number;
  student_name: string;
  email: string;
  tracked_count: number;
  understood_count: number;
  in_progress_count: number;
  last_activity?: string;
}

export interface ClassProgressResponse {
  classroom_id: number;
  classroom_name: string;
  total_students: number;
  students: StudentProgressSummary[];
  aggregate: {
    total_tracked: number;
    total_understood: number;
    total_in_progress: number;
    avg_understood: number;
  };
}

// ================== KAZANIM ANALYTICS TYPES ==================

export interface KazanimStatistic {
  kazanim_code: string;
  kazanim_description: string;
  grade?: number;
  subject?: string;
  understood_count: number;
  in_progress_count: number;
  tracked_count: number;
  total_students: number;
  mastery_rate: number;
}

export interface KazanimAnalyticsResponse {
  classroom_id: number;
  classroom_name: string;
  total_students: number;
  most_understood: KazanimStatistic[];
  least_understood: KazanimStatistic[];
  all_kazanimlar: KazanimStatistic[];
  summary: {
    avg_mastery_rate: number;
    total_unique_kazanimlar: number;
  };
}

// ================== STUDENT PROGRESS DETAIL TYPES ==================

export interface CurriculumKazanim {
  code: string;
  description: string;
  title?: string;
  semester?: number;
  grade?: number;
  subject?: string;
}

export type StudentKazanimStatus = 'understood' | 'in_progress' | 'tracked' | 'not_started';

export interface StudentKazanimProgressItem {
  kazanim_code: string;
  status: StudentKazanimStatus;
  initial_confidence_score?: number;
  understanding_confidence?: number;
  tracked_at?: string;
  understood_at?: string;
}

export interface StudentProgressDetailResponse {
  student: {
    id: number;
    full_name: string;
    email: string;
    grade?: number;
  };
  classroom: {
    id: number;
    name: string;
    grade: number;
    subject?: string;
  };
  summary: {
    tracked: number;
    in_progress: number;
    understood: number;
    not_started: number;
    total: number;
  };
  progress_by_code: Record<string, StudentKazanimProgressItem>;
  curriculum: CurriculumKazanim[];
}

// ================== ASSIGNMENT TYPES ==================

export type AssignmentType = 'practice' | 'exam' | 'homework';
export type SubmissionStatus = 'pending' | 'started' | 'submitted' | 'graded';

export interface Assignment {
  id: number;
  title: string;
  description?: string;
  assignment_type: AssignmentType;
  target_kazanimlar: string[];
  exam_id?: string;
  assigned_at: string;
  due_at?: string;
  is_active: boolean;
  created_at: string;
  classroom_count?: number;
  submission_count?: number;
}

export interface AssignmentListResponse {
  items: Assignment[];
  total: number;
}

export interface CreateAssignmentRequest {
  title: string;
  description?: string;
  assignment_type: AssignmentType;
  target_kazanimlar?: string[];
  exam_id?: string;
  due_at?: string;
}

export interface AssignmentSubmission {
  id: number;
  student_id: number;
  student_name: string;
  status: SubmissionStatus;
  started_at?: string;
  submitted_at?: string;
  score?: number;
  max_score?: number;
}

export interface DistributeAssignmentRequest {
  classroom_ids: number[];
  due_at_override?: string;
}

// ================== SCHOOL USER MANAGEMENT TYPES ==================

export interface SchoolUser {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  grade?: number;
  is_active: boolean;
  created_at: string;
  last_login?: string;
}

export interface SchoolUserListResponse {
  items: SchoolUser[];
  total: number;
  page: number;
  page_size: number;
}

export interface InviteUserRequest {
  email: string;
  role: 'student' | 'teacher' | 'school_admin';
  grade?: number;
}
