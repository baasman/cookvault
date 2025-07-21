# CookVault

A modern recipe digitization platform that uses OCR and AI to extract recipes from cookbook images and organize them into collections.

## Overview

CookVault allows users to upload images of cookbook pages and automatically extract structured recipe data using advanced OCR and natural language processing. The platform supports user collections, recipe organization, comments, and notes.

## Features

- **OCR Recipe Extraction**: Upload cookbook images and get structured recipe data
- **AI-Powered Parsing**: Uses Anthropic Claude to intelligently parse recipe text
- **User Collections**: Organize recipes into custom collections 
- **Recipe Groups**: Create themed groups of related recipes
- **Comments & Notes**: Add personal notes and comments to recipes
- **Cookbook Search**: Search and discover cookbooks via Google Books API
- **Copy Functionality**: Easily copy recipes for sharing
- **Copyright Compliance**: Built-in copyright consent and rules

## Tech Stack

### Frontend
- **React 19** with TypeScript
- **Vite** for build tooling
- **TailwindCSS** for styling
- **React Router** for navigation
- **React Query** for API state management
- **React Hook Form** for form handling

### Backend
- **Flask** web framework
- **SQLAlchemy** ORM with SQLite/PostgreSQL
- **Flask-Migrate** for database migrations
- **Tesseract OCR** for image text extraction
- **Anthropic Claude API** for recipe parsing
- **Google Books API** for cookbook metadata
- **Redis** for caching
- **Gunicorn** WSGI server

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- UV package manager
- Docker & Docker Compose (recommended)

### Development Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd cookbook-creator
   ```

2. **Backend setup**:
   ```bash
   cd backend
   uv pip install -e .
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Database setup**:
   ```bash
   # Using UV (recommended)
   uv run flask db upgrade
   
   # Or with Docker
   docker-compose up -d
   ```

4. **Frontend setup**:
   ```bash
   cd frontend
   npm install
   ```

5. **Start development servers**:
   ```bash
   # Backend
   cd backend && python run.py
   
   # Frontend (in another terminal)
   cd frontend && npm run dev
   ```

### Docker Development

```bash
# Start all services
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f
```

## API Endpoints

### Public API
- `GET /health` - Health check
- `GET /api/health` - Detailed health status
- `GET /api/cookbooks/search` - Search cookbooks

### Recipes API
- `POST /api/recipes/upload` - Upload recipe image
- `GET /api/recipes` - List user recipes
- `GET /api/recipes/{id}` - Get recipe details
- `PUT /api/recipes/{id}` - Update recipe
- `DELETE /api/recipes/{id}` - Delete recipe

### Collections API
- `GET /api/recipes/collections` - List user collections
- `POST /api/recipes/collections` - Create collection
- `PUT /api/recipes/collections/{id}` - Update collection
- `DELETE /api/recipes/collections/{id}` - Delete collection

### Recipe Groups API
- `GET /api/recipe-groups` - List recipe groups
- `POST /api/recipe-groups` - Create recipe group
- `GET /api/recipe-groups/{id}` - Get group details

## Database CLI Tools

The project includes several CLI utilities for database management:

```bash
# Database management
uv run cookbook-db-manager

# Run migrations  
uv run cookbook-db-migrate

# Seed development data
uv run cookbook-db-seed

# Development helpers
uv run cookbook-db-dev

# General database utilities
uv run cookbook-db-utils
```

## Environment Configuration

### Required Environment Variables

```bash
# Flask configuration
SECRET_KEY=your-secure-secret-key
FLASK_ENV=development

# Database
DATABASE_URL=sqlite:///cookbook_dev.db  # Development
# DATABASE_URL=postgresql://user:pass@host:port/db  # Production

# Redis (optional, for caching)
REDIS_URL=redis://localhost:6379/0

# API Keys
ANTHROPIC_API_KEY=your-anthropic-api-key
GOOGLE_BOOKS_API_KEY=your-google-books-api-key  # Optional

# CORS settings
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Upload settings
MAX_CONTENT_LENGTH=16777216  # 16MB
UPLOAD_FOLDER=uploads
```

## Deployment

### Production Deployment (Render - Recommended)

```bash
# Install Render CLI
brew install render

# Login to Render
render login

# Configure environment
cp .env.production.example .env.production
# Edit .env.production with your values

# Deploy both frontend and backend
./render-deploy.sh
```

### Docker Production Deployment

```bash
# Build and start production stack
docker-compose -f docker-compose.prod.yml up -d

# Run database migrations
docker-compose -f docker-compose.prod.yml exec app flask db upgrade
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

## Development

### Code Quality

```bash
# Frontend
cd frontend
npm run lint        # ESLint
npm run build       # TypeScript check + build

# Backend  
cd backend
uv run ruff check   # Linting
uv run black .      # Formatting
uv run mypy .       # Type checking
```

### Testing

```bash
# Backend tests
cd backend
uv run pytest

# Frontend tests (when implemented)
cd frontend  
npm test
```

### Database Migrations

```bash
# Create migration
uv run flask db migrate -m "Description of changes"

# Apply migrations
uv run flask db upgrade

# Downgrade (if needed)
uv run flask db downgrade
```

## Architecture

```
Frontend (React + Vite) → Flask API → Database (SQLite/PostgreSQL)
                                  → Redis (caching)
                                  → Tesseract OCR
                                  → Anthropic Claude API
                                  → Google Books API
```

## File Structure

```
cookbook-creator/
├── frontend/              # React frontend application
│   ├── src/
│   │   ├── components/    # Reusable UI components
│   │   ├── pages/         # Page components
│   │   ├── services/      # API service layers
│   │   ├── types/         # TypeScript type definitions
│   │   └── utils/         # Utility functions
│   └── package.json
├── backend/               # Flask backend application  
│   ├── app/
│   │   ├── api/          # API route handlers
│   │   ├── models/       # SQLAlchemy models
│   │   ├── services/     # Business logic services
│   │   └── utils/        # Utility functions
│   ├── migrations/       # Database migration files
│   ├── cookbook_db_utils/ # CLI database utilities
│   └── tests/            # Backend tests
├── docker-compose.yml    # Development Docker setup
├── docker-compose.prod.yml # Production Docker setup
├── render.yaml           # Render deployment blueprint
└── pyproject.toml        # Python project configuration
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`  
3. Make your changes and test them
4. Run code quality checks
5. Commit your changes: `git commit -m "Add new feature"`
6. Push to the branch: `git push origin feature/new-feature`
7. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- Check the [DEPLOYMENT.md](DEPLOYMENT.md) for deployment-specific issues
- Review the backend [README](backend/README.md) for backend-specific documentation
- Open an issue on GitHub for bug reports or feature requests