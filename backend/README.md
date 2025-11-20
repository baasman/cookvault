# Cookbook Creator Backend

Backend API for Cookbook Creator - AI-powered recipe digitization and cookbook management platform.

## Overview

Flask-based REST API providing:
- AI-powered recipe extraction from images using Anthropic Claude
- Recipe and cookbook management
- User authentication and authorization
- Premium subscriptions via Stripe
- Cloud image storage via Cloudinary
- Print-on-demand integration with Lulu

## Setup

### Prerequisites
- Python 3.11+
- `uv` package manager - Install with: `pip install uv`
- PostgreSQL (or use SQLite for development)
- Redis (recommended for caching and sessions)

### Installation

1. **Install dependencies:**
```bash
uv sync
```

2. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Initialize database:**
```bash
uv run python scripts/cookbook_db_cli.py init
uv run python scripts/cookbook_db_cli.py migrate
```

4. **Seed test data (optional):**
```bash
uv run python scripts/cookbook_db_cli.py seed users-only
```

## Development

### Run locally
```bash
uv run python run.py
```

The API will be available at http://localhost:5001

### Run tests
```bash
uv run pytest
```

### Database operations

The project includes a powerful CLI for database management:

```bash
# Run migrations
uv run python scripts/cookbook_db_cli.py migrate

# Create migration
uv run python scripts/cookbook_db_cli.py create-migration "description"

# Seed data
uv run python scripts/cookbook_db_cli.py seed all

# Create admin user
uv run python scripts/cookbook_db_cli.py create-user --email admin@example.com --admin
```

See [Database CLI Documentation](../docs/operations/database-cli.md) for complete reference.

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/auth/me` - Get current user

### Recipes
- `GET /api/recipes` - List recipes
- `POST /api/recipes` - Create recipe
- `GET /api/recipes/:id` - Get recipe details
- `PUT /api/recipes/:id` - Update recipe
- `DELETE /api/recipes/:id` - Delete recipe
- `POST /api/recipes/upload` - Upload recipe image (AI extraction)

### Cookbooks
- `GET /api/cookbooks` - List cookbooks
- `POST /api/cookbooks` - Create cookbook
- `GET /api/cookbooks/:id` - Get cookbook
- `PUT /api/cookbooks/:id` - Update cookbook
- `DELETE /api/cookbooks/:id` - Delete cookbook

### Payments
- `POST /api/payments/subscription/upgrade` - Upgrade subscription
- `POST /api/payments/webhook` - Stripe webhook handler

See [Complete API Documentation](../docs/api/README.md) for all endpoints.

## Architecture

```
React Frontend → Flask API → PostgreSQL (Database)
                          → Redis (Caching & Sessions)
                          → Anthropic Claude (AI Recipe Extraction)
                          → Cloudinary (Image Storage)
                          → Stripe (Payments)
                          → Lulu (Print-on-Demand)
```

## Technology Stack

- **Flask 3.0** - Web framework
- **SQLAlchemy 2.0** - ORM
- **PostgreSQL/SQLite** - Database
- **Redis** - Caching and session storage
- **Anthropic Claude** - AI-powered recipe parsing
- **Cloudinary** - Cloud image storage and CDN
- **Stripe** - Payment processing
- **Flask-JWT-Extended** - Authentication
- **Gunicorn** - Production WSGI server

## Project Structure

```
backend/
├── app/                    # Application code
│   ├── api/               # API route handlers
│   ├── models/            # Database models
│   ├── services/          # Business logic
│   └── utils/             # Utility functions
├── scripts/               # Utility scripts
│   ├── cookbook_db_cli.py # Database CLI tool
│   └── seed_data/         # Sample data
├── tests/                 # Test files
├── migrations/            # Database migrations
└── run.py                 # Application entry point
```

## Environment Variables

Key environment variables (see `.env.example` for complete list):

```bash
# Flask
FLASK_ENV=development
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://user:pass@localhost/cookbook_creator

# Redis
REDIS_URL=redis://localhost:6379/0

# API Keys
ANTHROPIC_API_KEY=your-anthropic-key
CLOUDINARY_URL=cloudinary://...
STRIPE_SECRET_KEY=your-stripe-key
```

See [Environment Variables Reference](../docs/deployment/environment-variables.md) for complete documentation.

## Docker Development

```bash
# Start all services (app, database, redis)
docker-compose up --build

# Run migrations in container
docker-compose exec app uv run python scripts/cookbook_db_cli.py migrate

# View logs
docker-compose logs -f app
```

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app tests/

# Run specific test file
uv run pytest tests/test_recipes.py
```

## Linting & Formatting

```bash
# Check code style
uv run ruff check .

# Format code
uv run ruff format .
```

## Documentation

For complete documentation, see:

- **[📚 Documentation Home](../docs/README.md)** - Central documentation hub
- **[🚀 Getting Started](../docs/getting-started/)** - Setup and installation
- **[🔌 API Reference](../docs/api/)** - Complete API documentation
- **[🏗️ Architecture](../docs/architecture/)** - System design
- **[🚢 Deployment](../docs/deployment/)** - Production deployment
- **[⚙️ Operations](../docs/operations/)** - Database management

## Contributing

See [Contributing Guide](../docs/development/contributing.md) for development workflow and coding standards.

## License

See [LICENSE](../LICENSE) file in the root directory.
