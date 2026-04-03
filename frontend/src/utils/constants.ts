/** File upload size limits in bytes */
export const FILE_LIMITS = {
  IMAGE_MAX_SIZE: 10 * 1024 * 1024,        // 10MB per image
  TOTAL_IMAGES_SIZE: 50 * 1024 * 1024,     // 50MB total for multi-upload
  VIDEO_MAX_SIZE: 100 * 1024 * 1024,       // 100MB per video
  MAX_IMAGES_PER_RECIPE: 10,
} as const;

/** Difficulty level colors */
export const DIFFICULTY_COLORS: Record<string, string> = {
  easy: '#22c55e',
  medium: '#f59e0b',
  hard: '#ef4444',
} as const;

/** App brand colors */
export const BRAND = {
  ACCENT: '#f15f1c',
  ACCENT_HOVER: '#d9541a',
  TEXT_PRIMARY: '#1c120d',
  TEXT_SECONDARY: '#9b644b',
  BORDER: '#e8d7cf',
  BACKGROUND: '#f1ece9',
  BACKGROUND_PAGE: '#fcf9f8',
} as const;
