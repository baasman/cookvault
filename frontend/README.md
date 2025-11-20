# Cookbook Creator Frontend

React-based frontend application for Cookbook Creator - AI-powered recipe digitization and cookbook management.

## Overview

Modern React application providing:
- AI-powered recipe upload and extraction
- Cookbook and recipe management
- Public recipe discovery and sharing
- Premium subscription features
- Responsive design with mobile support

## Technology Stack

- **React 19** - Latest UI framework with concurrent features
- **TypeScript 5.8** - Advanced type safety
- **Vite 6** - Ultra-fast build tool
- **TanStack Query v5** - Server state management and caching
- **React Router v7** - Client-side routing
- **Tailwind CSS v4** - Utility-first styling
- **React Hook Form** - Form management
- **Headless UI** - Accessible components
- **Heroicons** - SVG icons

## Setup

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation

1. **Install dependencies:**
```bash
npm install
```

2. **Set up environment variables:**
```bash
cp .env.example .env.local
# Edit .env.local with your configuration
```

3. **Required environment variables:**
```bash
VITE_API_URL=http://localhost:5001/api
VITE_STRIPE_PUBLIC_KEY=your-stripe-public-key  # If using payments
```

## Development

### Run development server
```bash
npm run dev
```

The application will be available at http://localhost:5173

### Build for production
```bash
npm run build
```

### Preview production build
```bash
npm run preview
```

### Run tests
```bash
npm test
```

### Lint code
```bash
npm run lint
```

### Format code
```bash
npm run format
```

## Available Scripts

- `npm run dev` - Start development server with hot reload
- `npm run build` - Build for production
- `npm run preview` - Preview production build locally
- `npm test` - Run tests with Vitest
- `npm run test:ui` - Run tests with UI
- `npm run test:coverage` - Run tests with coverage report
- `npm run lint` - Lint code with ESLint
- `npm run format` - Format code with Prettier
- `npm run typecheck` - Check TypeScript types

## Project Structure

```
frontend/
├── src/
│   ├── components/       # Reusable UI components
│   │   ├── cookbook/    # Cookbook-specific components
│   │   ├── recipe/      # Recipe-specific components
│   │   ├── upload/      # Upload and processing components
│   │   └── ui/          # Generic UI components
│   ├── pages/           # Page components
│   ├── services/        # API service layer
│   ├── contexts/        # React contexts (auth, etc.)
│   ├── hooks/           # Custom React hooks
│   ├── utils/           # Utility functions
│   ├── types/           # TypeScript type definitions
│   └── App.tsx          # Root application component
├── public/              # Static assets
└── index.html           # HTML entry point
```

## Key Features

### Recipe Upload & Management
- Drag-and-drop image upload
- AI-powered recipe extraction
- Manual recipe editing
- Recipe organization into cookbooks

### Cookbook Management
- Create and organize cookbooks
- Public/private cookbook settings
- Share cookbooks with community
- Print-on-demand integration

### User Features
- User authentication
- Premium subscriptions
- Recipe favorites and collections
- Public profile and sharing

## API Integration

The frontend communicates with the Flask backend API. Key service layers:

- **AuthService** - User authentication and registration
- **RecipeService** - Recipe CRUD operations
- **CookbookService** - Cookbook management
- **UploadService** - Image upload and processing
- **PaymentService** - Stripe integration

See [API Documentation](../docs/api/README.md) for endpoint details.

## State Management

Using **TanStack Query** for:
- Server state management
- Automatic caching
- Background refetching
- Optimistic updates
- Request deduplication

## Styling

Using **Tailwind CSS** with:
- Utility-first approach
- Custom design tokens
- Dark mode support (if enabled)
- Responsive breakpoints
- Component-scoped styles

## Testing

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with UI
npm run test:ui

# Generate coverage report
npm run test:coverage
```

## Environment Variables

### Development (.env.local)
```bash
VITE_API_URL=http://localhost:5001/api
VITE_STRIPE_PUBLIC_KEY=pk_test_...
```

### Production
```bash
VITE_API_URL=https://your-api-domain.com/api
VITE_STRIPE_PUBLIC_KEY=pk_live_...
```

See [Environment Variables Reference](../docs/deployment/environment-variables.md) for complete list.

## Build & Deployment

### Production Build

```bash
# Build optimized production bundle
npm run build

# Output will be in dist/ directory
```

### Deployment

The frontend can be deployed to:
- **Render** (Static Site) - Recommended
- **Vercel** - Automatic deployments
- **Netlify** - Easy setup
- **AWS S3 + CloudFront** - Custom infrastructure
- **Any static hosting** - Just serve the dist/ folder

See [Deployment Guide](../docs/deployment/production.md) for detailed instructions.

## Code Style

- **TypeScript** - Strict mode enabled
- **ESLint** - Enforced code standards
- **Prettier** - Consistent formatting
- **Naming Conventions:**
  - PascalCase for components and types
  - camelCase for functions and variables
  - kebab-case for file names

## Performance Optimization

- Code splitting with React.lazy()
- Image optimization with next/image equivalent
- Memoization with React.memo() and useMemo()
- Lazy loading for routes
- Bundle size monitoring

## Accessibility

- Semantic HTML
- ARIA labels where needed
- Keyboard navigation support
- Screen reader friendly
- Color contrast compliance

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- ES2020+ features
- No IE11 support

## Documentation

For complete documentation, see:

- **[📚 Documentation Home](../docs/README.md)** - Central documentation hub
- **[🚀 Getting Started](../docs/getting-started/)** - Setup guide
- **[🏗️ Architecture](../docs/architecture/)** - Frontend architecture details
- **[💻 Development Guide](../docs/development/)** - Development workflow
- **[🚢 Deployment](../docs/deployment/)** - Production deployment

## Contributing

See [Contributing Guide](../docs/development/contributing.md) for development workflow and coding standards.

## Troubleshooting

### Port already in use
```bash
# Kill process on port 5173
lsof -ti:5173 | xargs kill -9

# Or use different port
npm run dev -- --port 3000
```

### API connection errors
- Verify `VITE_API_URL` in `.env.local`
- Ensure backend is running
- Check CORS configuration in backend

### Build errors
- Clear node_modules: `rm -rf node_modules && npm install`
- Clear Vite cache: `rm -rf node_modules/.vite`
- Check TypeScript errors: `npm run typecheck`

## License

See [LICENSE](../LICENSE) file in the root directory.
