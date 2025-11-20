# Getting Started with Cookbook Creator

**Tags:** `getting-started`, `installation`, `setup`, `onboarding`
**Last updated:** 2025-11-14

Welcome to Cookbook Creator! This guide will help you set up your development environment and start contributing.

---

## Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** - Backend runtime
- **Node.js 18+** - Frontend development
- **PostgreSQL 14+** (or SQLite for local development)
- **Redis** (optional for local development)
- **Git** - Version control

---

## Quick Start

Get up and running in 5 minutes:

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/cookbook-creator.git
cd cookbook-creator

# 2. Set up backend
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync
cp .env.example .env
# Edit .env with your configuration

# 3. Set up database
uv run python scripts/cookbook_db_cli.py init
uv run python scripts/cookbook_db_cli.py migrate

# 4. Start backend server
uv run python run.py

# 5. In a new terminal, set up frontend
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local with your configuration

# 6. Start frontend development server
npm run dev
```

Your application should now be running at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:5001

---

## Detailed Guides

### Installation
➡️ **[Full Installation Guide](installation.md)**

Complete step-by-step installation instructions including:
- System requirements
- Installing all dependencies
- Database setup
- Configuration

### Development Setup
➡️ **[Development Setup Guide](development-setup.md)**

Configure your development environment:
- IDE setup (VS Code, PyCharm)
- Git hooks and pre-commit
- Environment variables
- Development tools

### First Contribution
➡️ **[First Contribution Guide](first-contribution.md)**

Make your first code contribution:
- Finding issues to work on
- Creating a feature branch
- Making changes
- Submitting a pull request

---

## Development Workflow

```
1. Create feature branch
   ↓
2. Make changes
   ↓
3. Write/update tests
   ↓
4. Run linting & tests
   ↓
5. Commit changes
   ↓
6. Push and create PR
   ↓
7. Code review
   ↓
8. Merge to main
```

---

## Common Tasks

### Running Tests

```bash
# Backend tests
cd backend
uv run pytest

# Frontend tests
cd frontend
npm test
```

### Database Operations

```bash
# Create a migration
uv run python scripts/cookbook_db_cli.py create-migration "description"

# Run migrations
uv run python scripts/cookbook_db_cli.py migrate

# Seed test data
uv run python scripts/cookbook_db_cli.py seed
```

### Linting and Formatting

```bash
# Backend
uv run ruff check .
uv run ruff format .

# Frontend
npm run lint
npm run format
```

---

## Project Structure

```
cookbook-creator/
├── backend/              # Flask backend application
│   ├── app/             # Application code
│   ├── migrations/      # Database migrations
│   ├── scripts/         # Utility scripts
│   └── tests/           # Backend tests
├── frontend/            # React frontend application
│   ├── src/            # Source code
│   ├── public/         # Static assets
│   └── tests/          # Frontend tests
├── docs/               # Documentation (you are here!)
└── .meridian/          # Project management files
```

---

## Next Steps

Once you have the project running:

1. **Understand the Architecture** → [Architecture Overview](../architecture/overview.md)
2. **Explore the API** → [API Reference](../api/README.md)
3. **Learn Code Standards** → [Code Standards](../development/code-standards.md)
4. **Start Contributing** → [Contributing Guide](../development/contributing.md)

---

## Getting Help

- **Installation issues:** Check [Troubleshooting](../deployment/troubleshooting.md)
- **Development questions:** See [Development Guide](../development/)
- **Architecture questions:** Read [Architecture docs](../architecture/)
- **Still stuck?:** Open an issue on GitHub

---

## See Also

- [Development Tools](../development/debugging.md)
- [Testing Guide](../development/testing.md)
- [Deployment Guide](../deployment/production.md)

---

[← Back to Documentation Home](../README.md)
