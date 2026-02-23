# Cookbook Creator Documentation

> **Welcome to the Cookbook Creator documentation hub!** 🍳
>
> This is your central resource for understanding, developing, and deploying the Cookbook Creator application.

**Last updated:** 2025-02-14

---

## 📖 Quick Start

**New to the project?** Start here:
1. [Installation Guide](getting-started/installation.md) - Set up your development environment
2. [Development Setup](getting-started/development-setup.md) - Configure local development
3. [First Contribution](getting-started/first-contribution.md) - Make your first code contribution
4. [Architecture Overview](architecture/overview.md) - Understand the system design

**Looking for something specific?** Use the navigation below or check our [Search Guide](SEARCH.md).

---

## 📚 Documentation Sections

### 🚀 Getting Started
**Path:** `/docs/getting-started/`

Essential guides for new developers joining the project.

- [Installation](getting-started/installation.md) - Install dependencies and prerequisites
- [Development Setup](getting-started/development-setup.md) - Configure your local environment
- [First Contribution](getting-started/first-contribution.md) - Step-by-step guide to contributing

---

### 🔌 API Reference
**Path:** `/docs/api/`

Complete API endpoint documentation with examples and schemas.

- [API Overview](api/README.md) - REST API introduction and conventions
- [Authentication](api/authentication.md) - Authentication and authorization
- [Recipe Endpoints](api/recipes-endpoints.md) - Recipe CRUD operations
- [Cookbook Endpoints](api/cookbooks-endpoints.md) - Cookbook management
- [Payment Endpoints](api/payments-endpoints.md) - Stripe integration and subscriptions

---

### 🏗️ Architecture
**Path:** `/docs/architecture/`

System design, technical decisions, and architectural patterns.

- [Architecture Overview](architecture/overview.md) - High-level system design
- [Frontend Architecture](architecture/frontend-architecture.md) - React, TypeScript, TanStack Query
- [Backend Architecture](architecture/backend-architecture.md) - Flask, SQLAlchemy, service patterns
- [Database Schema](architecture/database-schema.md) - Data models and relationships

---

### 💻 Development
**Path:** `/docs/development/`

Guidelines, standards, and tools for active development.

- [Contributing Guide](development/contributing.md) - How to contribute code
- [Load Testing](development/load-testing.md) - Performance testing suite
- [Local HTTPS Setup](development/local-https-setup.md) - HTTPS for local development

---

### 🚢 Deployment
**Path:** `/docs/deployment/`

Production deployment guides and operational procedures.

- [Production Deployment](deployment/production.md) - Deploy to production (Render)
- [Environment Variables](deployment/environment-variables.md) - Configuration reference
- [Troubleshooting](deployment/troubleshooting.md) - Common deployment issues

---

### ⚙️ Operations
**Path:** `/docs/operations/`

Database administration, maintenance, and operational tasks.

- [Database CLI](operations/database-cli.md) - CLI tool for database operations
- [Database Migrations](operations/migrations.md) - Schema changes and migrations

---

### 🔗 Integrations
**Path:** `/docs/integrations/`

Third-party service integrations and configuration.

- [Anthropic Claude](integrations/anthropic-claude.md) - AI-powered recipe extraction
- [Cloudinary](integrations/cloudinary.md) - Image storage and transformations
- [Stripe](integrations/stripe.md) - Payment processing
- [Lulu Print](integrations/lulu-print.md) - Print-on-demand cookbook publishing

---

### 📋 Planning
**Path:** `/docs/planning/`

Roadmaps, feature planning, and business strategy.

- [Project Roadmap](planning/roadmap.md) - Upcoming features and milestones

---

## 🔍 Finding Information

### Quick Search Tips

**Using GitHub Search:**
- Press `/` to focus the search bar
- Search within files: `path:docs/ your-search-term`
- Search by file type: `extension:md authentication`

**Using Command Line:**
```bash
# Search all markdown files in docs
grep -r "search term" docs/ --include="*.md"

# Find files by name
find docs/ -name "*recipe*"

# Search with context (3 lines before/after)
grep -r -C 3 "search term" docs/
```

**Need more help?** Check our detailed [Search Guide](SEARCH.md) with common grep patterns and search examples.

---

## 🏷️ Documentation by Topic

### Authentication & Security
- [API Authentication](api/authentication.md)
- [Environment Variables](deployment/environment-variables.md)

### Database
- [Database Schema](architecture/database-schema.md)
- [Database CLI](operations/database-cli.md)
- [Migrations](operations/migrations.md)

### AI & Machine Learning
- [Anthropic Claude Integration](integrations/anthropic-claude.md)
- [Recipe Extraction](api/recipes-endpoints.md)

### Payment & Subscriptions
- [Stripe Integration](integrations/stripe.md)
- [Payment Endpoints](api/payments-endpoints.md)

### Images & Media
- [Cloudinary Integration](integrations/cloudinary.md)
- [Image Upload Endpoints](api/recipes-endpoints.md)

### Print Publishing
- [Lulu Print Integration](integrations/lulu-print.md)

---

## 📝 Documentation Standards

All documentation in this project follows these standards:

### File Naming
- Use `kebab-case.md` for all markdown files
- Use descriptive names: `database-cli.md` not `db.md`

### Document Structure
Each document should include:
1. **Title** - Clear H1 heading
2. **Description** - Brief overview of the document
3. **Tags** - Keywords for searchability
4. **Content** - Main documentation content
5. **See Also** - Links to related documentation

### Code Examples
- Use language-specific code blocks (```python, ```typescript)
- Include comments explaining non-obvious code
- Test all code examples before committing

### Links
- Use relative links for internal documentation
- Use absolute URLs for external resources
- Keep link text descriptive: `[API Authentication Guide](api/authentication.md)` not `[click here](api/authentication.md)`

---

## 🤝 Contributing to Documentation

Found an error or want to improve the docs?

1. **Small fixes:** Edit directly and submit a PR
2. **New sections:** Discuss in an issue first
3. **Major rewrites:** Create a proposal document

See our [Contributing Guide](development/contributing.md) for detailed instructions.

---

## 📦 What's Included in This Project

**Cookbook Creator** is a full-stack web application for managing recipes and creating cookbooks.

### Tech Stack

**Frontend:**
- React 19 + TypeScript 5.8
- Vite 6 (build tool)
- TanStack Query (state management)
- Tailwind CSS (styling)

**Backend:**
- Flask 3.0 + Python 3.11+
- SQLAlchemy 2.0 (ORM)
- PostgreSQL (production) / SQLite (development)
- Redis (caching)

**Key Integrations:**
- **Anthropic Claude** - AI-powered recipe extraction from images
- **Cloudinary** - Image storage and transformations
- **Stripe** - Payment processing and subscriptions
- **Lulu** - Print-on-demand cookbook publishing

### Key Features
- 📸 AI-powered recipe extraction from images
- 📚 Cookbook management and organization
- 👥 Recipe groups and collections
- 💳 Premium subscriptions
- 🌐 Public recipe sharing
- 📖 Print-on-demand cookbook publishing
- 📄 PDF cookbook processing

---

## ❓ Getting Help

- **Documentation issues:** [Report in GitHub Issues](../issues)
- **Code questions:** Check [Architecture docs](architecture/) first
- **API questions:** See [API Reference](api/)
- **Deployment issues:** Check [Troubleshooting Guide](deployment/troubleshooting.md)

---

## 📜 License

See [LICENSE](../LICENSE) in the root directory.

---

**Happy coding! 🍳**
