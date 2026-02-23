# Development Guide

**Tags:** `development`, `contributing`, `testing`, `standards`
**Last updated:** 2025-02-14

Guidelines, standards, and tools for developing Cookbook Creator.

---

## Development Resources

### Contributing
➡️ **[Contributing Guide](contributing.md)**

- Code of conduct
- How to contribute
- Pull request process
- Review guidelines

### Load Testing
➡️ **[Load Testing Guide](load-testing.md)**

- Performance testing suite
- Load test scenarios
- Benchmark results

### Local HTTPS
➡️ **[Local HTTPS Setup](local-https-setup.md)**

- Certificate generation
- HTTPS configuration for local development

---

## Development Workflow

### 1. Pick an Issue
Browse [open issues](https://github.com/yourusername/cookbook-creator/issues) and find one labeled `good-first-issue` or `help-wanted`.

### 2. Create a Branch
```bash
git checkout -b feature/your-feature-name
```

### 3. Make Changes
- Write code following our [code standards](code-standards.md)
- Add/update tests
- Update documentation

### 4. Test Locally
```bash
# Backend tests
cd backend
uv run pytest

# Frontend tests
cd frontend
npm test

# Run linting
cd backend && uv run ruff check .
cd frontend && npm run lint
```

### 5. Commit Changes
```bash
git add .
git commit -m "feat: add new feature"
```

Follow [Conventional Commits](https://www.conventionalcommits.org/) format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test changes
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

### 6. Push and Create PR
```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

---

## Development Tools

### Required Tools
- **Python 3.11+** with `uv` package manager
- **Node.js 18+** with `npm`
- **Git** for version control
- **PostgreSQL 14+** (or use SQLite for local dev)
- **Redis** (optional for local development)

### Recommended Tools
- **VS Code** - IDE with Python and TypeScript extensions
- **Postman** - API testing
- **pgAdmin** - PostgreSQL GUI
- **Redis Commander** - Redis GUI

### IDE Setup

**VS Code Extensions:**
- Python
- Pylance
- ESLint
- Prettier
- Tailwind CSS IntelliSense

**VS Code Settings:**
```json
{
  "python.linting.enabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  }
}
```

---

## Environment Setup

### Backend Environment Variables

Create `backend/.env`:
```bash
FLASK_ENV=development
DATABASE_URL=postgresql://user:pass@localhost/cookbook_creator
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-secret-key
ANTHROPIC_API_KEY=your-api-key
CLOUDINARY_URL=your-cloudinary-url
STRIPE_SECRET_KEY=your-stripe-key
```

### Frontend Environment Variables

Create `frontend/.env.local`:
```bash
VITE_API_URL=http://localhost:5001/api
VITE_STRIPE_PUBLIC_KEY=your-stripe-public-key
```

---

## Development Servers

### Start Backend
```bash
cd backend
source .venv/bin/activate
uv run python run.py
```

Backend runs at: http://localhost:5001

### Start Frontend
```bash
cd frontend
npm run dev
```

Frontend runs at: http://localhost:5173

---

## Common Development Tasks

### Add a New API Endpoint
1. Create route handler in `backend/app/routes/`
2. Add service logic in `backend/app/services/`
3. Update tests in `backend/tests/`
4. Document in `docs/api/`

### Add a New React Component
1. Create component in `frontend/src/components/`
2. Add TypeScript types
3. Write component tests
4. Update Storybook (if applicable)

### Database Migration
```bash
# Create migration
cd backend
uv run python scripts/cookbook_db_cli.py create-migration "description"

# Review generated migration in backend/migrations/

# Apply migration
uv run python scripts/cookbook_db_cli.py migrate
```

---

## See Also

- [Getting Started](../getting-started/README.md)
- [Architecture](../architecture/README.md)
- [Load Testing](load-testing.md)

---

[← Back to Documentation Home](../README.md)
