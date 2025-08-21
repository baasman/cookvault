# Cookbook Creator 🍳

A modern web application for digitizing, managing, and sharing recipes from cookbooks. Upload cookbook pages, automatically extract recipes using AI, and organize them into beautiful collections with professional cloud storage and advanced features.

## ✨ Features

### Core Features
- **📸 Smart Recipe Extraction**: Upload images or PDFs of cookbook pages and automatically extract structured recipe data
- **🤖 AI-Powered Parsing**: Uses Anthropic Claude with intelligent retry logic for reliable recipe processing
- **☁️ Cloud Image Storage**: Cloudinary integration for fast, optimized image delivery via CDN
- **📚 Cookbook Management**: Organize recipes into cookbooks and collections
- **👥 Public Sharing**: Share recipes publicly while maintaining copyright compliance
- **🔍 Search & Discovery**: Browse and discover public recipes from the community
- **📝 Recipe Groups**: Create themed groups like "Quick Weeknight Meals" or "Holiday Favorites"
- **💬 Social Features**: Add comments and personal notes to recipes
- **🖼️ Advanced Image Handling**: Smart image optimization, thumbnails, and responsive display

### Advanced Features
- **💳 Premium Subscriptions**: Stripe-powered payment system with tiered features
- **⚡ High Performance**: Redis caching for lightning-fast response times
- **🔄 Batch Processing**: Upload multiple cookbook pages at once with robust processing
- **📖 Google Books Integration**: Automatically fetch cookbook metadata and covers
- **📜 Historical Recipe Support**: Special handling for vintage cookbooks with old measurements
- **🎯 Multi-format Support**: Works with PDFs, images (JPG, PNG, WebP), and text
- **⚖️ Copyright Management**: Built-in copyright consent and compliance system
- **🔒 Enterprise Security**: Advanced session management, rate limiting, and security headers

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (optional, SQLite for development)
- Redis (recommended for caching and sessions)
- uv (Python package manager) - `pip install uv`

#### Installing Redis (Optional but Recommended)

**macOS (Homebrew)**:
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
```

**Windows**: Download from [Redis for Windows](https://github.com/MicrosoftArchive/redis/releases)

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
- **React 19** - Latest UI framework with concurrent features
- **TypeScript 5.8** - Advanced type safety and modern JavaScript
- **TanStack Query v5** - Powerful data fetching, caching, and synchronization
- **React Router v7** - Modern client-side routing with data loading
- **Tailwind CSS v4** - Next-generation utility-first styling
- **Vite 6** - Ultra-fast build tool with advanced optimizations
- **React Hook Form** - Performant form management with validation
- **React Hot Toast** - Elegant toast notifications
- **Headless UI** - Accessible component primitives
- **Heroicons** - Beautiful SVG icons

### Backend
- **Flask 3.0** - Modern Python web framework
- **SQLAlchemy 2.0** - Advanced ORM with async support
- **PostgreSQL/SQLite** - Database (PostgreSQL for production, SQLite for development)
- **Flask-JWT-Extended** - Secure JWT authentication with refresh tokens
- **Anthropic Claude** - AI-powered recipe parsing with retry logic
- **Redis 5+** - In-memory caching and session storage
- **Cloudinary** - Cloud-based image storage, optimization, and CDN
- **Stripe** - Payment processing and subscription management
- **Pillow** - Advanced image processing and optimization
- **pdfplumber** - Intelligent PDF text extraction
- **Google Books API** - Cookbook metadata and cover images
- **Flask-Limiter** - Rate limiting and abuse prevention
- **Flask-Talisman** - Security headers and HTTPS enforcement

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
POST   /api/recipes/upload          - Upload single recipe image
POST   /api/recipes/upload-multi    - Upload multiple recipe images  
POST   /api/recipes/upload-text     - Upload recipe as text
GET    /api/recipes/job-status/:id  - Check processing job status
GET    /api/recipes/multi-job-status/:id - Check multi-image job status
POST   /api/recipes/:id/images      - Add images to existing recipe
```

### Payments (Premium Features)
```
POST   /api/payments/subscription/upgrade     - Create subscription upgrade
POST   /api/payments/subscription/cancel      - Cancel subscription  
GET    /api/payments/user/subscription        - Get user subscription status
GET    /api/payments/user/payments           - Get payment history
GET    /api/payments/user/purchases          - Get purchase history
POST   /api/payments/cookbook/:id/purchase   - Purchase individual cookbook
POST   /api/payments/webhook                 - Stripe webhook endpoint
```

### Recipe Groups
```
GET    /api/recipe-groups           - List user's recipe groups
POST   /api/recipe-groups           - Create new recipe group
GET    /api/recipe-groups/:id       - Get group details
PUT    /api/recipe-groups/:id       - Update recipe group
DELETE /api/recipe-groups/:id       - Delete recipe group
POST   /api/recipe-groups/:id/recipes/:recipeId - Add recipe to group
DELETE /api/recipe-groups/:id/recipes/:recipeId - Remove recipe from group
```

## 🔧 Configuration

### Backend Environment Variables (.env)

```env
# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-change-in-production

# Database
DATABASE_URL=postgresql://cookbook_user:cookbook_pass@localhost:5432/cookbook_db
# Or for SQLite (development): sqlite:///cookbook.db

# Redis (for caching and sessions)
REDIS_URL=redis://localhost:6379/0

# AI Services
ANTHROPIC_API_KEY=your-anthropic-api-key

# Cloudinary (Cloud Image Storage)
CLOUDINARY_CLOUD_NAME=your-cloudinary-cloud-name
CLOUDINARY_API_KEY=your-cloudinary-api-key
CLOUDINARY_API_SECRET=your-cloudinary-api-secret
USE_CLOUDINARY=true  # Set to false to use local storage

# Stripe (Payment Processing) - Optional
STRIPE_SECRET_KEY=sk_test_your-stripe-secret-key
STRIPE_PUBLISHABLE_KEY=pk_test_your-stripe-publishable-key
STRIPE_WEBHOOK_SECRET=whsec_your-webhook-secret
STRIPE_PREMIUM_PRICE=299  # Price in cents ($2.99)
FREE_TIER_UPLOAD_LIMIT=10  # Max uploads for free users

# File Upload & Processing
UPLOAD_FOLDER=uploads/
MAX_CONTENT_LENGTH=16777216  # 16MB
MAX_IMAGE_DIMENSION=1200  # Max image size for processing
JPEG_QUALITY=85  # JPEG compression quality (1-100)
MAX_UPLOAD_SIZE=8  # Max upload size in MB

# OCR Configuration
OCR_QUALITY_THRESHOLD=8  # Quality threshold (1-10)
OCR_ENABLE_LLM_FALLBACK=true  # Use Claude when OCR quality is low
OCR_QUALITY_CACHE_TTL=3600  # Cache TTL in seconds

# Security & Sessions
SESSION_COOKIE_SECURE=false  # Set to true in production with HTTPS
SESSION_COOKIE_DOMAIN=localhost  # Set your domain in production
SESSION_COOKIE_SAMESITE=Lax  # Use 'None' for cross-origin in production
PERMANENT_SESSION_LIFETIME=3600  # Session timeout in seconds

# CORS (for production)
CORS_ORIGINS=http://localhost:5173,https://yourdomain.com

# Rate Limiting
RATELIMIT_STORAGE_URL=redis://localhost:6379/1

# Optional Services
GOOGLE_BOOKS_API_KEY=your-google-books-api-key

# Logging (Production)
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_FILE=logs/cookbook-creator.log
LOG_MAX_BYTES=10485760  # 10MB
LOG_BACKUP_COUNT=10
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

## ☁️ Cloudinary Setup (Recommended)

Cloudinary provides professional image storage, optimization, and CDN delivery for better performance and reliability.

### Setting up Cloudinary

1. **Create Account**: Sign up at [cloudinary.com](https://cloudinary.com)
2. **Get Credentials**: From your dashboard, copy:
   - Cloud Name
   - API Key  
   - API Secret
3. **Configure Environment**: Add to your `.env` file:
   ```env
   CLOUDINARY_CLOUD_NAME=your-cloud-name
   CLOUDINARY_API_KEY=your-api-key
   CLOUDINARY_API_SECRET=your-api-secret
   USE_CLOUDINARY=true
   ```

### Cloudinary Features

- **Automatic Optimization**: Images are automatically compressed and served in optimal formats (WebP, AVIF)
- **Smart Resizing**: Dynamic image resizing and thumbnail generation
- **CDN Delivery**: Global CDN for fast image loading worldwide  
- **Backup & Reliability**: Professional-grade image storage and backup
- **Bandwidth Savings**: Reduces server load and bandwidth costs

### Local vs Cloudinary Storage

The app supports both local file storage and Cloudinary:

- **Development**: Can use local storage (`USE_CLOUDINARY=false`)
- **Production**: Highly recommended to use Cloudinary for scalability
- **Migration**: Existing local images continue to work alongside Cloudinary

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

1. **Environment Variables**: Set all production environment variables (see configuration section)
2. **Database**: Set up PostgreSQL database with connection pooling
3. **Redis**: Set up Redis instance for caching and sessions
4. **Cloudinary**: Configure cloud image storage (highly recommended)
5. **Stripe**: Set up payment processing if using premium features
6. **Migrations**: Run `flask db upgrade` to create database schema
7. **Frontend Build**: Run `npm run build` to create production build
8. **Static Files**: Serve frontend build with nginx/CDN
9. **HTTPS**: Configure SSL certificates (required for payments)
10. **Security**: Configure CORS, session security, and rate limiting
11. **Monitoring**: Set up error tracking (e.g., Sentry) and logging
12. **Backup**: Set up database backups and image backup strategy

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build individually
docker build -t cookbook-backend ./backend
docker build -t cookbook-frontend ./frontend
```

### Render.com Deployment

The project is configured for easy deployment on Render with full stack support:

#### Required Services
1. **PostgreSQL Database**: Create a managed PostgreSQL database
2. **Redis Instance**: Create a managed Redis instance for caching
3. **Web Service** (Backend): Deploy the Flask API
4. **Static Site** (Frontend): Deploy the React application

#### Optional Services  
5. **Cloudinary**: External service for image storage (recommended)
6. **Stripe**: External service for payment processing (if using premium features)

#### Deployment Steps
1. Connect your GitHub repository to Render
2. Create PostgreSQL database and note the connection string
3. Create Redis instance and note the connection string  
4. Create web service for backend:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn run:app`
   - Set all environment variables from the configuration section
5. Create static site for frontend:
   - Build Command: `npm install && npm run build`
   - Publish Directory: `dist`
6. Configure Cloudinary and Stripe externally
7. Deploy and test!

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

**CORS errors**: Ensure your frontend URL is in the backend's CORS_ORIGINS environment variable

**Database connection errors**: Check DATABASE_URL and ensure PostgreSQL is running with proper credentials

**Redis connection errors**: Verify REDIS_URL is correct and Redis server is accessible

**Session/Authentication issues**: Check SESSION_COOKIE_DOMAIN and security settings match your deployment

**Image upload failures**: 
- Check UPLOAD_FOLDER permissions for local storage
- Verify Cloudinary credentials if using cloud storage
- Ensure MAX_CONTENT_LENGTH and MAX_UPLOAD_SIZE are appropriate

**AI parsing errors**: 
- Verify ANTHROPIC_API_KEY is valid and has credits
- Check for API rate limiting (429 errors) - the app has built-in retry logic
- Monitor OCR_QUALITY_THRESHOLD settings

**Payment processing issues**: 
- Ensure Stripe keys match your environment (test vs live)
- Verify webhook endpoints are properly configured
- Check STRIPE_WEBHOOK_SECRET matches your Stripe dashboard

**Performance issues**:
- Ensure Redis is connected for caching
- Consider enabling Cloudinary for faster image delivery
- Monitor database connection pooling in production

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Anthropic Claude** - AI-powered recipe parsing with intelligent retry logic
- **Cloudinary** - Professional cloud image storage and optimization
- **Stripe** - Secure and reliable payment processing
- **Redis** - Lightning-fast in-memory data storage and caching
- **React & Flask Communities** - Amazing frameworks and ecosystems  
- **Tailwind CSS** - Beautiful utility-first styling system
- **TanStack Query** - Powerful data synchronization for React
- **Heroicons** - Beautiful SVG icon library
- **Headless UI** - Accessible component primitives
- **All Contributors** - Thank you for making this project better!

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/cookbook-creator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/cookbook-creator/discussions)
- **Email**: support@cookbookcreator.com

---

**Built with ❤️ for home cooks and food lovers everywhere** 🥘

*Happy cooking and happy coding!*