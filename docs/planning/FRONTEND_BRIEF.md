# Frontend Development Brief: Cookbook Creator

## Project Overview

Build a modern, responsive web application for digitizing cookbook recipes using OCR/AI technology. The frontend will provide an intuitive interface for uploading recipe images, managing cookbooks, and viewing digitized recipes with structured data.

### Existing Design Assets

**Important**: There are existing HTML templates with UI designs located in `backend/app/api/templates/` directory. These templates show the intended UI structure and visual design for the application. While the structure and formatting can be completely changed during React implementation, these templates serve as:

- **Design Reference**: Visual layout and component organization
- **Feature Scope**: What functionality needs to be implemented
- **User Flow**: How users will navigate through the application
- **Styling Direction**: Color schemes, typography, and component patterns

The React implementation should draw inspiration from these templates while improving the user experience with modern component architecture and responsive design.

## Technology Stack

### Core Technologies
- **React 18+** - Modern component-based UI framework
- **TypeScript** - Type safety and better developer experience
- **Tailwind CSS** - Utility-first CSS framework for rapid styling
- **React Router** - Client-side routing and navigation

### Build Tools & Development
- **Vite** - Fast build tool and development server
- **ESLint + Prettier** - Code quality and formatting
- **Tailwind CSS IntelliSense** - VS Code extension for better DX

### HTTP & State Management
- **Axios** - HTTP client for API communication
- **React Query/TanStack Query** - Server state management and caching
- **React Hook Form** - Form handling and validation
- **Zustand** - Lightweight client state management (if needed)

### UI Components & Icons
- **Headless UI** - Unstyled, accessible UI components
- **Heroicons** - Beautiful SVG icons by Tailwind team
- **React Hot Toast** - Elegant notifications

## API Integration

### Backend Endpoints
The frontend will integrate with the following Flask API endpoints:

#### Recipes
- `GET /api/recipes` - List recipes with pagination
- `GET /api/recipes/{id}` - Get single recipe details
- `POST /api/recipes/upload` - Upload recipe image with optional cookbook info

#### Processing Jobs
- `GET /api/jobs/{id}` - Check OCR processing status

#### Cookbooks (Future)
- `GET /api/cookbooks` - List cookbooks
- `POST /api/cookbooks` - Create new cookbook
- `GET /api/cookbooks/{id}` - Get cookbook details

### Data Models (TypeScript Interfaces)

```typescript
interface Cookbook {
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

interface Recipe {
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

interface Ingredient {
  id: number;
  name: string;
  quantity?: number;
  unit?: string;
  preparation?: string;
  optional: boolean;
  order: number;
}

interface Instruction {
  id: number;
  step_number: number;
  text: string;
}

interface Tag {
  id: number;
  name: string;
}

interface ProcessingJob {
  id: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message?: string;
  recipe_id?: number;
  created_at: string;
  completed_at?: string;
}

interface UploadResponse {
  message: string;
  job_id: number;
  image_id: number;
  cookbook?: Cookbook;
  page_number?: number;
}
```

## Core Features & User Stories

### 1. Recipe Upload & Processing
**User Story**: As a user, I want to upload a recipe image and have it digitized automatically.

**Features**:
- Drag & drop image upload interface
- Optional cookbook selection and page number input
- Real-time processing status with progress indicators
- Image preview before upload
- Support for multiple image formats (PNG, JPG, JPEG, GIF, BMP, TIFF)

### 2. Recipe Management
**User Story**: As a user, I want to view and manage my digitized recipes.

**Features**:
- Recipe list view with search and filtering
- Detailed recipe view with formatted ingredients and instructions
- Edit recipe information
- Tag-based organization
- Cookbook-based grouping

### 3. Cookbook Management
**User Story**: As a user, I want to organize recipes by cookbook.

**Features**:
- Create and manage cookbooks
- Link recipes to specific cookbooks with page numbers
- Cookbook overview with recipe count
- Browse recipes by cookbook

### 4. Search & Discovery
**User Story**: As a user, I want to easily find recipes.

**Features**:
- Global search across recipes
- Filter by cookbook, tags, difficulty, cook time
- Sort by date, name, cook time
- Tag-based browsing

## Application Structure

### Page Hierarchy
```
/                     - Landing page with upload interface
/recipes              - Recipe list with filters
/recipes/:id          - Individual recipe detail
/cookbooks            - Cookbook management
/cookbooks/:id        - Cookbook detail with recipes
/upload               - Dedicated upload page
/processing/:jobId    - Processing status page
```

### Component Architecture
```
src/
├── components/
│   ├── ui/           # Reusable UI components
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Input.tsx
│   │   ├── Modal.tsx
│   │   └── Spinner.tsx
│   ├── forms/        # Form components
│   │   ├── UploadForm.tsx
│   │   ├── CookbookSelector.tsx
│   │   └── RecipeForm.tsx
│   ├── recipe/       # Recipe-specific components
│   │   ├── RecipeCard.tsx
│   │   ├── RecipeDetail.tsx
│   │   ├── IngredientList.tsx
│   │   └── InstructionList.tsx
│   └── layout/       # Layout components
│       ├── Header.tsx
│       ├── Navigation.tsx
│       └── Layout.tsx
├── pages/            # Page components
├── hooks/            # Custom React hooks
├── services/         # API service functions
├── types/            # TypeScript type definitions
├── utils/            # Utility functions
└── styles/           # Global styles
```

## Key User Interface Requirements

### 1. Upload Interface
- **Drag & Drop Zone**: Large, prominent area for dropping images
- **File Browser**: Traditional file selection as fallback
- **Image Preview**: Show uploaded image before processing
- **Cookbook Selection**: Dropdown to select existing cookbook (optional)
- **Page Number Input**: Number input for cookbook page reference
- **Progress Indicator**: Real-time status during OCR processing

### 2. Recipe Display
- **Clean Typography**: Easy-to-read ingredient lists and instructions
- **Step-by-Step Instructions**: Numbered, well-spaced instruction steps
- **Ingredient Formatting**: Clear quantity, unit, and preparation display
- **Metadata Display**: Cook time, prep time, servings, difficulty
- **Tag Pills**: Visual tag representation
- **Cookbook Reference**: Show source cookbook and page number

### 3. Navigation & Search
- **Global Search**: Prominent search bar in header
- **Filter Sidebar**: Collapsible filters for recipes
- **Breadcrumb Navigation**: Clear navigation path
- **Responsive Design**: Mobile-first approach

### 4. Processing Feedback
- **Loading States**: Elegant loading indicators during processing
- **Error Handling**: Clear error messages with retry options
- **Success Notifications**: Confirmation when recipes are created
- **Processing Status**: Live updates during OCR processing

## Responsive Design Requirements

### Breakpoints (Tailwind CSS)
- **Mobile**: 320px - 768px (sm)
- **Tablet**: 768px - 1024px (md/lg)
- **Desktop**: 1024px+ (xl/2xl)

### Mobile-First Features
- Touch-friendly upload interface
- Collapsible navigation menu
- Simplified recipe card layout
- Bottom sheet modals for mobile
- Optimized image loading

## Development Phases

### Phase 0: Design Analysis (Week 1)
- [ ] Review existing HTML templates in `backend/app/api/templates/`
- [ ] Extract design patterns, color schemes, and component structure
- [ ] Identify key user flows and functionality requirements
- [ ] Create component mapping from templates to React architecture
- [ ] Plan responsive adaptations and improvements

### Phase 1: Core Upload (Week 1-2)
- [ ] Project setup with Vite, React, TypeScript, Tailwind
- [ ] Implement layout and navigation based on template designs
- [ ] Build image upload interface with drag & drop (referencing template UX)
- [ ] API integration for upload endpoint
- [ ] Processing status polling
- [ ] Basic recipe display following template structure

### Phase 2: Recipe Management (Week 3-4)
- [ ] Recipe list with pagination
- [ ] Recipe detail view with full formatting
- [ ] Search and filter functionality
- [ ] Responsive design implementation
- [ ] Error handling and loading states

### Phase 3: Cookbook Integration (Week 5)
- [ ] Cookbook selection in upload
- [ ] Cookbook management interface
- [ ] Recipe-cookbook associations
- [ ] Enhanced navigation

### Phase 4: Polish & Optimization (Week 6)
- [ ] Performance optimization
- [ ] Advanced UI interactions
- [ ] Comprehensive error handling
- [ ] Testing and bug fixes
- [ ] Documentation

## Performance Requirements

### Core Web Vitals
- **LCP (Largest Contentful Paint)**: < 2.5s
- **FID (First Input Delay)**: < 100ms
- **CLS (Cumulative Layout Shift)**: < 0.1

### Optimization Strategies
- **Image Optimization**: Lazy loading, WebP format, responsive images
- **Code Splitting**: Route-based and component-based splitting
- **Caching**: Aggressive caching with React Query
- **Bundle Size**: Keep initial bundle < 200KB gzipped

## Accessibility Requirements

### WCAG 2.1 AA Compliance
- **Keyboard Navigation**: Full keyboard accessibility
- **Screen Reader Support**: Proper ARIA labels and roles
- **Color Contrast**: Minimum 4.5:1 contrast ratio
- **Focus Management**: Clear focus indicators
- **Alternative Text**: Image alt attributes for all images

### Inclusive Design
- **Loading States**: Clear progress indicators for screen readers
- **Error Messages**: Descriptive, actionable error messages
- **Form Labels**: Clear, associated form labels
- **Semantic HTML**: Proper heading hierarchy and landmarks

## Testing Strategy

### Unit Testing
- **Vitest** - Fast unit test runner
- **React Testing Library** - Component testing
- **Mock Service Worker** - API mocking

### Integration Testing
- **Playwright** - End-to-end testing
- **User journey testing** - Critical path testing

### Test Coverage
- Aim for 80%+ test coverage
- Focus on critical user journeys
- Test error scenarios and edge cases

## Deployment & Environment

### Development Environment
```bash
npm create vite@latest cookbook-frontend -- --template react-ts
cd cookbook-frontend
npm install
npm install -D tailwindcss postcss autoprefixer @types/node
npm install axios @tanstack/react-query react-router-dom react-hook-form
npm install @headlessui/react @heroicons/react react-hot-toast
npx tailwindcss init -p
```

### Build & Deployment
- **Production Build**: Optimized bundle with Vite
- **Static Hosting**: Deploy to Vercel, Netlify, or similar
- **Environment Variables**: API base URL configuration
- **CI/CD**: Automated testing and deployment

### Backend Integration
- **API Base URL**: Configurable via environment variables
- **CORS Configuration**: Ensure backend allows frontend domain
- **File Upload**: Handle multipart/form-data requests
- **Error Handling**: Graceful handling of API errors

## Design System & Branding

### Reference Templates
Before implementing the design system, review the existing HTML templates in `backend/app/api/templates/` to:
- Extract the actual color palette and branding used
- Understand the established visual hierarchy
- Identify existing component patterns and layouts
- Maintain consistency with the designed user experience

### Color Palette (Tailwind)
*Note: Adjust these based on the actual colors used in the template designs*
- **Primary**: Emerald (green-500, green-600)
- **Secondary**: Slate (slate-100 to slate-900)
- **Accent**: Orange (orange-500)
- **Success**: Green (green-500)
- **Warning**: Yellow (yellow-500)
- **Error**: Red (red-500)

### Typography
- **Primary Font**: Inter (clean, modern)
- **Headings**: Font weights 600-700
- **Body Text**: Font weight 400
- **Code/Monospace**: JetBrains Mono

### Component Patterns
- **Cards**: Subtle shadows, rounded corners
- **Buttons**: Solid primary, outline secondary
- **Form Elements**: Consistent padding, focus states
- **Loading States**: Skeleton screens and spinners

This brief provides a comprehensive foundation for building a modern, user-friendly cookbook creator frontend that integrates seamlessly with the Flask backend API.