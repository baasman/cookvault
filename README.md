# Cookbook Creator 🍳

A modern web application for digitizing, managing, and sharing recipes from cookbooks. Upload cookbook pages, automatically extract recipes using AI, and organize them into beautiful collections.

## ✨ Features

### Core Features
- **📸 Smart Recipe Extraction**: Upload images or PDFs of cookbook pages and automatically extract structured recipe data
- **🤖 AI-Powered Parsing**: Uses Anthropic Claude to intelligently parse recipes, ingredients, and instructions
- **📚 Cookbook Management**: Organize recipes into cookbooks and collections
- **👥 Public Sharing**: Share recipes publicly while maintaining copyright compliance
- **🔍 Search & Discovery**: Browse and discover public recipes from the community
- **📝 Recipe Groups**: Create themed groups like "Quick Weeknight Meals" or "Holiday Favorites"
- **💬 Social Features**: Add comments and personal notes to recipes
- **🖼️ Image Support**: Upload and display beautiful recipe images

### Advanced Features
- **Batch Processing**: Upload multiple cookbook pages at once
- **Google Books Integration**: Automatically fetch cookbook metadata
- **Historical Recipe Support**: Special handling for vintage cookbooks with old measurements
- **Multi-format Support**: Works with PDFs, images (JPG, PNG), and text
- **Copyright Management**: Built-in copyright consent and compliance system

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (optional, SQLite for development)
- uv (Python package manager) - `pip install uv`

### Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install uv
uv pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Initialize database
uv run python -m cookbook_db_utils.cli --env development db create
uv run python -m cookbook_db_utils.cli --env development seed users-only

# Run development server
uv run python run.py
```

The backend will be available at http://localhost:5001

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local
# Edit .env.local with your API URL

# Run development server
npm run dev
```

The frontend will be available at http://localhost:5173

## 📁 Project Structure

```
cookbook-creator/
├── frontend/                 # React frontend application
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   │   ├── cookbook/   # Cookbook-specific components
│   │   │   ├── recipe/     # Recipe-specific components
│   │   │   ├── upload/     # Upload and processing components
│   │   │   └── ui/         # Generic UI components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API service layer
│   │   ├── contexts/       # React contexts (auth, etc.)
│   │   ├── hooks/          # Custom React hooks
│   │   ├── utils/          # Utility functions
│   │   └── types/          # TypeScript type definitions
│   └── public/             # Static assets
│
├── backend/                 # Flask backend application
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── models/         # Database models
│   │   ├── services/       # Business logic services
│   │   └── utils/          # Utility functions
│   ├── migrations/         # Database migrations
│   ├── tests/             # Test files
│   ├── cookbook_db_utils/  # Database utilities & CLI
│   └── scripts/           # Utility scripts
│       └── seed_data/     # Sample data for development
│
└── docs/                   # Documentation
```

## 🛠️ Technology Stack

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **React Query (TanStack Query)** - Data fetching & caching
- **React Router v6** - Client-side routing
- **Tailwind CSS** - Utility-first styling
- **Vite** - Lightning-fast build tool
- **React Hook Form** - Form management
- **React Hot Toast** - Toast notifications

### Backend
- **Flask** - Python web framework
- **SQLAlchemy** - ORM for database interactions
- **PostgreSQL/SQLite** - Database (PostgreSQL for production, SQLite for development)
- **JWT** - Secure authentication
- **Anthropic Claude** - AI-powered recipe parsing
- **Pillow** - Image processing
- **pdfplumber** - PDF text extraction
- **Google Books API** - Cookbook metadata

## 📚 API Documentation

### Authentication
```
POST   /api/auth/register     - Register new user
POST   /api/auth/login        - User login
POST   /api/auth/logout       - User logout
GET    /api/auth/me           - Get current user
POST   /api/auth/refresh      - Refresh JWT token
```

### Recipes
```
GET    /api/recipes           - List recipes (filtered by user/public)
POST   /api/recipes           - Create recipe
GET    /api/recipes/:id       - Get recipe details
PUT    /api/recipes/:id       - Update recipe
DELETE /api/recipes/:id       - Delete recipe
PUT    /api/recipes/:id/privacy - Toggle recipe privacy
POST   /api/recipes/:id/copy  - Copy recipe to collection
POST   /api/recipes/:id/images - Upload recipe image
```

### Cookbooks
```
GET    /api/cookbooks         - List cookbooks
POST   /api/cookbooks         - Create cookbook
GET    /api/cookbooks/:id     - Get cookbook details
PUT    /api/cookbooks/:id     - Update cookbook
DELETE /api/cookbooks/:id     - Delete cookbook
GET    /api/cookbooks/:id/recipes - Get cookbook recipes
```

### Public API (No Auth Required)
```
GET    /api/public/recipes    - Browse public recipes
GET    /api/public/cookbooks  - Browse public cookbooks
GET    /api/public/cookbooks/:id - View public cookbook
GET    /api/public/cookbooks/:id/recipes - View public cookbook recipes
```

### Upload & Processing
```
POST   /api/upload/image      - Upload single image for processing
POST   /api/upload/multi-image - Upload multiple images
POST   /api/upload/pdf        - Upload PDF for processing
GET    /api/processing/:jobId - Check processing status
```

## 🔧 Configuration

### Backend Environment Variables (.env)

```env
# Flask Configuration
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-change-in-production

# Database (PostgreSQL for production)
DATABASE_URL=postgresql://user:password@localhost/cookbook_db
# Or for SQLite (development):
# DATABASE_URL=sqlite:///instance/cookbook.db

# Authentication
JWT_SECRET_KEY=your-jwt-secret-change-in-production
JWT_ACCESS_TOKEN_EXPIRES=86400

# AI Services
ANTHROPIC_API_KEY=your-anthropic-api-key

# File Upload
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216  # 16MB

# Optional Services
GOOGLE_BOOKS_API_KEY=your-google-books-api-key
```

### Frontend Environment Variables (.env.local)

```env
# API Configuration
VITE_API_URL=http://localhost:5001/api

# Optional: For production
VITE_APP_NAME="Cookbook Creator"
VITE_APP_DESCRIPTION="Digital recipe management"
```

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest tests/

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_recipes.py
```

### Frontend Tests
```bash
cd frontend
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch
```

## 📦 Database Management

The project includes a powerful CLI for database operations:

### Basic Commands
```bash
# Create database tables
uv run python -m cookbook_db_utils.cli db create

# Drop all tables (careful!)
uv run python -m cookbook_db_utils.cli db drop

# Reset database (drop + create + seed)
uv run python -m cookbook_db_utils.cli db reset

# Check database status
uv run python -m cookbook_db_utils.cli db status
```

### Data Seeding
```bash
# Seed only users (recommended for development)
uv run python -m cookbook_db_utils.cli seed users-only

# Seed all sample data
uv run python -m cookbook_db_utils.cli seed all

# Import cookbook from PDF
uv run python -m cookbook_db_utils.cli seed pdf-cookbook path/to/cookbook.pdf
```

### Data Export/Import
```bash
# Export all content (creates ZIP with images)
uv run python -m cookbook_db_utils.cli utils export-content --output backup.zip

# Import content and assign to admin
uv run python -m cookbook_db_utils.cli utils import-to-admin backup.zip

# Export for migration between environments
uv run python -m cookbook_db_utils.cli utils export-all --include-users
```

## 🚢 Deployment

### Production Checklist

1. **Environment Variables**: Set all production environment variables
2. **Database**: Set up PostgreSQL database
3. **Migrations**: Run `flask db upgrade`
4. **Frontend Build**: Run `npm run build`
5. **Static Files**: Serve frontend build with nginx/CDN
6. **HTTPS**: Configure SSL certificates
7. **Monitoring**: Set up error tracking (e.g., Sentry)

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build individually
docker build -t cookbook-backend ./backend
docker build -t cookbook-frontend ./frontend
```

### Render.com Deployment

The project is configured for easy deployment on Render:

1. Connect your GitHub repository
2. Create a PostgreSQL database
3. Create a web service for the backend
4. Create a static site for the frontend
5. Set environment variables
6. Deploy!

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on:
- Code of conduct
- Development workflow
- Pull request process
- Coding standards

### Quick Contribution Guide

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 🐛 Troubleshooting

### Common Issues

**CORS errors**: Ensure your frontend URL is in the backend's CORS settings

**Database connection errors**: Check DATABASE_URL and ensure PostgreSQL is running

**JWT errors**: Verify JWT_SECRET_KEY matches between frontend/backend

**Upload failures**: Check UPLOAD_FOLDER permissions and MAX_CONTENT_LENGTH

**AI parsing errors**: Verify ANTHROPIC_API_KEY is valid and has credits

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Anthropic Claude** - AI-powered recipe parsing
- **React & Flask Communities** - Amazing frameworks and ecosystems
- **Tailwind CSS** - Beautiful utility-first styling
- **Heroicons** - Beautiful SVG icons
- **All Contributors** - Thank you for making this project better!

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/cookbook-creator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/cookbook-creator/discussions)
- **Email**: support@cookbookcreator.com

---

**Built with ❤️ for home cooks and food lovers everywhere** 🥘

*Happy cooking and happy coding!*