// API Response Types based on backend analysis

export interface Cookbook {
  id: number;
  title: string;
  author?: string;
  description?: string;
  publisher?: string;
  isbn?: string;
  publication_date?: string;
  cover_image_url?: string;
  recipe_count: number;
  user_id?: number; // Owner of the cookbook
  created_at: string;
  updated_at: string;
  recipes?: Recipe[]; // Only populated in detail view
  // Purchase-related fields
  is_purchasable?: boolean;
  price?: number;
  purchase_count?: number;
  has_purchased?: boolean;
  is_available_for_purchase?: boolean;
}

export interface Ingredient {
  id: number;
  name: string;
  quantity?: number;
  unit?: string;
  preparation?: string;
  optional: boolean;
  order: number;
}

export interface Instruction {
  id: number;
  step_number: number;
  text: string;
}

export interface Tag {
  id: number;
  name: string;
}

export interface RecipeImage {
  id: number;
  filename: string;
  original_filename: string;
  file_size: number;
  content_type: string;
  uploaded_at: string;
  image_order?: number;
  page_number?: number;
}

export interface RecipeNote {
  id: number;
  user_id: number;
  recipe_id: number;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface RecipeComment {
  id: number;
  recipe_id: number;
  user_id: number;
  content: string;
  created_at: string;
  updated_at: string;
  user?: {
    id: number;
    username: string;
    first_name?: string;
    last_name?: string;
  };
}

export interface Recipe {
  id: number;
  title: string;
  description?: string;
  cookbook?: Cookbook;
  page_number?: number;
  prep_time?: number;
  cook_time?: number;
  servings?: number;
  difficulty?: string;
  source?: string;
  user_id?: number;
  is_public: boolean;
  published_at?: string;
  user?: {
    id: number;
    username: string;
    first_name?: string;
    last_name?: string;
  };
  ingredients: Ingredient[];
  instructions: Instruction[];
  tags: Tag[];
  images?: RecipeImage[];
  created_at: string;
  updated_at: string;
  is_in_collection?: boolean;
  user_note?: RecipeNote | null;
  groups?: {
    id: number;
    name: string;
    description?: string;
  }[];
  has_full_access?: boolean;
  paywall_message?: string;
}

export interface ProcessingJob {
  id: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message?: string;
  recipe_id?: number;
  created_at: string;
  completed_at?: string;
  is_multi_image?: boolean;
  multi_job_id?: number;
  image_order?: number;
  ocr_text?: string;
  ocr_confidence?: number;
  ocr_method?: string;
}

export interface MultiRecipeJob {
  id: number;
  user_id: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  total_images: number;
  processed_images: number;
  recipe_id?: number;
  combined_ocr_text?: string;
  error_message?: string;
  created_at: string;
  completed_at?: string;
  processing_jobs?: ProcessingJob[];
}

export interface UploadResponse {
  message: string;
  job_id: number;
  recipe_id?: number;
  image_id?: number;
  cookbook?: Cookbook;
  page_number?: number;
}

export interface MultiUploadResponse {
  multi_job_id: number;
  total_images: number;
  message: string;
}

export interface MultiJobStatusResponse extends MultiRecipeJob {
  processing_jobs?: ProcessingJob[];
  recipe?: Recipe;
}

// API Response wrapper types
export interface RecipesResponse {
  recipes: Recipe[];
  total: number;
  pages: number;
  current_page: number;
}

export interface PublicRecipesResponse {
  recipes: Recipe[];
  pagination: {
    page: number;
    pages: number;
    per_page: number;
    total: number;
    has_next: boolean;
    has_prev: boolean;
    next_num?: number;
    prev_num?: number;
  };
}

export interface UserPublicRecipesResponse {
  user: {
    id: number;
    username: string;
    first_name?: string;
    last_name?: string;
  };
  recipes: Recipe[];
  pagination: {
    page: number;
    pages: number;
    per_page: number;
    total: number;
    has_next: boolean;
    has_prev: boolean;
    next_num?: number;
    prev_num?: number;
  };
}

export interface PublicStatsResponse {
  public_recipes: number;
  contributing_users: number;
  recent_recipes: number;
}

export interface CommentsResponse {
  comments: RecipeComment[];
  total: number;
  pages: number;
  current_page: number;
  per_page: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface ApiError {
  error: string;
}

// Form types
export interface UploadFormData {
  image: File | null;
  images: File[]; // For multi-image uploads
  isMultiImage: boolean; // Toggle between single and multi-image mode
  cookbook_id?: number;
  page_number?: number;
  // Upload mode selection
  no_cookbook?: boolean;
  // New cookbook creation fields
  create_new_cookbook?: boolean;
  new_cookbook_title?: string;
  new_cookbook_author?: string;
  new_cookbook_description?: string;
  new_cookbook_publisher?: string;
  new_cookbook_isbn?: string;
  new_cookbook_publication_date?: string;
  // Existing cookbook search fields
  search_existing_cookbook?: boolean;
  selected_existing_cookbook_id?: number;
  cookbook_search_query?: string;
  // Google Books search fields
  search_google_books?: boolean;
  selected_google_book?: any; // GoogleBook type from cookbooksApi
}

export interface ImagePreview {
  file: File;
  preview: string;
  id: string;
  order: number;
}

export interface RecipeFormData {
  title: string;
  description?: string;
  cookbook_id?: number;
  page_number?: number;
  prep_time?: number;
  cook_time?: number;
  servings?: number;
  difficulty?: string;
  ingredients: string[];
  instructions: string[];
  tags: string[];
}

// UI Component Props Types
export interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'pill' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
  className?: string;
}

export interface InputProps {
  label?: string;
  placeholder?: string;
  value?: string;
  onChange?: (value: string) => void;
  disabled?: boolean;
  required?: boolean;
  error?: string;
  type?: 'text' | 'email' | 'password' | 'number' | 'search' | 'date';
  icon?: React.ReactNode;
  className?: string;
}

export interface TextareaProps {
  label?: string;
  placeholder?: string;
  value?: string;
  onChange?: (value: string) => void;
  disabled?: boolean;
  required?: boolean;
  error?: string;
  rows?: number;
  className?: string;
}

export interface RecipeCardProps {
  recipe: Recipe;
  onClick?: () => void;
}

export interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

// Navigation and routing types
export interface NavItem {
  label: string;
  href: string;
  active?: boolean;
}

// Filter and search types
export interface FilterOptions {
  search: string;
  favorites: boolean;
  toCook: boolean;
  cookbook?: number;
  difficulty?: string;
  maxCookTime?: number;
}

export interface SortOptions {
  field: 'title' | 'created_at' | 'cook_time' | 'difficulty';
  direction: 'asc' | 'desc';
}

// User Profile Types
export interface UserProfile {
  user: UserInfo;
  statistics: UserStatistics;
  recent_activity: RecentActivity[];
}

export interface UserInfo {
  id: number;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  bio?: string;
  avatar_url?: string;
  role: string;
  status: string;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
  last_login?: string;
}

export interface UserStatistics {
  total_recipes: number;
  total_cookbooks: number;
  difficulty_breakdown: {
    easy: number;
    medium: number;
    hard: number;
    unspecified: number;
  };
  avg_cook_time_minutes: number;
  avg_recipes_per_cookbook: number;
  most_popular_cookbook?: {
    id: number;
    title: string;
    recipe_count: number;
  };
  cookbooks_with_recipes: number;
  empty_cookbooks: number;
}

export interface RecentActivity {
  type: 'recipe' | 'cookbook';
  id: number;
  title: string;
  created_at: string;
  cookbook_title?: string;
}