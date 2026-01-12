/**
 * Yediiklim AI Design System - Theme Constants
 *
 * Port of the original website.html design language:
 * - Warm stone color palette
 * - Glassmorphism effects
 * - Typography scales
 */

// Color Palette
export const colors = {
  paper: '#FDFCF8',    // --c-paper (off-white)
  canvas: '#E7E5E4',   // --c-canvas (warm grey background)
  ink: '#1C1917',      // --c-ink (dark brown/black)
  sepia: '#78350F',    // --c-sepia (warm brown accent)
  accent: '#9A3412',   // Gradient accent (darker sepia)
} as const;

// Font Families
export const fonts = {
  serif: "'Cormorant Garamond', serif",      // Headings, display text
  sans: "'Inter', sans-serif",               // Body text
  mono: "'JetBrains Mono', monospace",       // Labels, code, badges
} as const;

// Glassmorphism Classes (matching CSS)
export const glass = {
  vellum: 'glass-vellum',   // Main glassmorphism cards
  input: 'glass-input',     // Input area glass effect
  card: 'card-surface',     // Solid paper cards
} as const;

// Spacing Scale (based on 8px grid)
export const spacing = {
  xs: '0.25rem',   // 4px
  sm: '0.5rem',    // 8px
  md: '1rem',      // 16px
  lg: '1.5rem',    // 24px
  xl: '2rem',      // 32px
  '2xl': '3rem',   // 48px
  '3xl': '4rem',   // 64px
} as const;

// Border Radius
export const radius = {
  sm: '0.5rem',    // 8px
  md: '0.75rem',   // 12px
  lg: '1rem',      // 16px
  xl: '1.5rem',    // 24px
  full: '9999px',  // Pill shape
} as const;

// Shadow Presets
export const shadows = {
  sm: '0 1px 2px 0 rgba(28, 25, 23, 0.05)',
  md: '0 4px 6px -1px rgba(28, 25, 23, 0.02), 0 2px 4px -1px rgba(28, 25, 23, 0.02)',
  lg: '0 12px 32px -8px rgba(28, 25, 23, 0.08)',
  sepia: '0 0 0 1px rgba(120, 53, 15, 0.1), 0 4px 16px rgba(120, 53, 15, 0.1)',
} as const;

// Animation Presets
export const animations = {
  enter: 'animate-enter',
  spin: 'animate-spin',
  pulse: 'animate-pulse',
} as const;

// API Configuration
// In Docker: uses /api proxy (VITE_API_BASE_URL not set or empty)
// In development: uses http://localhost:8001 directly
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

// Application Routes
export const routes = {
  // Public
  landing: '/',
  login: '/giris',
  register: '/kayit',
  pricing: '/fiyatlar',
  forgotPassword: '/sifremi-unuttum',

  // Protected
  dashboard: '/panel',
  chat: '/sohbet',
  chatWithId: (id: string) => `/sohbet/${id}`,
  settings: '/ayarlar',
} as const;

// Grade Levels (Turkish educational system - all levels)
export const grades = [
  // İlkokul (Primary School)
  { value: 1, label: '1. Sınıf', level: 'İlkokul' },
  { value: 2, label: '2. Sınıf', level: 'İlkokul' },
  { value: 3, label: '3. Sınıf', level: 'İlkokul' },
  { value: 4, label: '4. Sınıf', level: 'İlkokul' },
  // Ortaokul (Middle School)
  { value: 5, label: '5. Sınıf', level: 'Ortaokul' },
  { value: 6, label: '6. Sınıf', level: 'Ortaokul' },
  { value: 7, label: '7. Sınıf', level: 'Ortaokul' },
  { value: 8, label: '8. Sınıf', level: 'Ortaokul' },
  // Lise (High School)
  { value: 9, label: '9. Sınıf', level: 'Lise' },
  { value: 10, label: '10. Sınıf', level: 'Lise' },
  { value: 11, label: '11. Sınıf', level: 'Lise' },
  { value: 12, label: '12. Sınıf', level: 'Lise' },
] as const;

// Subjects grouped by education level (Turkish)
export const subjects = [
  // Core subjects (all levels)
  { value: 'Matematik', label: 'Matematik', icon: '📐' },
  { value: 'Türkçe', label: 'Türkçe', icon: '📖' },
  // Science subjects (varies by level)
  { value: 'Fen Bilimleri', label: 'Fen Bilimleri', icon: '🔬' },  // İlkokul/Ortaokul
  { value: 'Biyoloji', label: 'Biyoloji', icon: '🧬' },            // Lise
  { value: 'Fizik', label: 'Fizik', icon: '⚛️' },                  // Lise
  { value: 'Kimya', label: 'Kimya', icon: '🧪' },                  // Lise
  // Social sciences
  { value: 'Sosyal Bilgiler', label: 'Sosyal Bilgiler', icon: '🌍' },  // İlkokul/Ortaokul
  { value: 'Tarih', label: 'Tarih', icon: '📜' },                      // Lise
  { value: 'Coğrafya', label: 'Coğrafya', icon: '🗺️' },               // Lise
  // Languages
  { value: 'İngilizce', label: 'İngilizce', icon: '🇬🇧' },
] as const;

// Exam modes with descriptions
export const examModes = {
  school: {
    value: false,
    label: 'Okul Modu',
    description: 'Sadece kendi sınıf seviyendeki içerikler gösterilir',
    icon: '🏫',
  },
  yks: {
    value: true,
    label: 'YKS/Sınav Modu',
    description: 'Sınıfından önceki tüm konular dahil edilir (kümülatif)',
    icon: '📚',
  },
} as const;
