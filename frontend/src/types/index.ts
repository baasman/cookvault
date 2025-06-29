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
  created_at: string;
  updated_at: string;
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
  ingredients: Ingredient[];
  instructions: Instruction[];
  tags: Tag[];
  created_at: string;
  updated_at: string;
}

export interface ProcessingJob {
  id: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message?: string;
  recipe_id?: number;
  created_at: string;
  completed_at?: string;
}

export interface UploadResponse {
  message: string;
  job_id: number;
  image_id: number;
  cookbook?: Cookbook;
  page_number?: number;
}

// API Response wrapper types
export interface RecipesResponse {
  recipes: Recipe[];
  total: number;
  pages: number;
  current_page: number;
}

export interface ApiError {
  error: string;
}

// Form types
export interface UploadFormData {
  image: File;
  cookbook_id?: number;
  page_number?: number;
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
  variant?: 'primary' | 'secondary' | 'pill';
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
  type?: 'text' | 'email' | 'password' | 'number' | 'search';
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