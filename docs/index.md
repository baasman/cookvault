# CookVault Documentation

Welcome to the CookVault documentation! This is your central resource for understanding, developing, and deploying the CookVault recipe management platform.

---

## Quick Start

**New to the project?** Start here:

1. [Getting Started](getting-started/README.md) - Set up your development environment
2. [Architecture Overview](architecture/README.md) - Understand the system design
3. [API Reference](api/README.md) - Explore the REST API
4. [Contributing Guide](development/contributing.md) - Make your first contribution

---

## Documentation Sections

### API Reference
Complete REST API documentation with examples and schemas.

- [API Overview](api/README.md) - Introduction and conventions
- [Authentication](api/authentication-endpoints.md) - Auth endpoints
- [Endpoints Reference](api/endpoints-reference.md) - All endpoints at a glance
- [Error Codes](api/error-codes.md) - Error handling

### Architecture
System design, technical decisions, and architectural patterns.

- [Architecture Overview](architecture/README.md) - High-level system design

### Development
Guidelines, standards, and tools for active development.

- [Contributing Guide](development/contributing.md) - How to contribute code
- [Load Testing](development/load-testing.md) - Performance testing suite
- [Local HTTPS Setup](development/local-https-setup.md) - HTTPS for local development

### Deployment
Production deployment guides and operational procedures.

- [Deployment Overview](deployment/README.md) - Deployment options
- [Production Deployment](deployment/production.md) - Deploy to production (Render)

### Operations
Database administration, maintenance, and operational tasks.

- [Database CLI](operations/database-cli.md) - CLI tool for database operations
- [Database Migrations](operations/database-migrations.md) - Schema changes and migrations
- [Backup & Restore](operations/backup-restore.md) - Data backup procedures
- [Monitoring](operations/monitoring.md) - System monitoring
- [Performance Baseline](operations/performance-baseline.md) - Performance benchmarks
- [Incident Response](operations/incident-response.md) - Handling incidents

### Integrations
Third-party service integrations and configuration.

- [Lulu Print](integrations/lulu-print.md) - Print-on-demand cookbook publishing

### Planning
Roadmaps, feature planning, and project briefs.

- [Project Brief](planning/PROJECT_BRIEF.md) - Project overview and goals

---

## Tech Stack

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

---

## Key Features

- AI-powered recipe extraction from images
- Cookbook management and organization
- Recipe groups and collections
- Premium subscriptions
- Public recipe sharing
- Print-on-demand cookbook publishing
- PDF cookbook processing

---

## Getting Help

- **Documentation issues:** [Report in GitHub Issues](https://github.com/baasman/cookvault/issues)
- **API questions:** See [API Reference](api/README.md)
- **Deployment issues:** Check [Deployment Guide](deployment/README.md)
