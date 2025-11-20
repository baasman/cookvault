# Architecture

**Tags:** `architecture`, `system-design`, `technical`
**Last updated:** 2025-11-14

Cookbook Creator system architecture, technical decisions, and design patterns.

---

## System Overview

Cookbook Creator is a full-stack web application with a React frontend and Flask backend, using PostgreSQL for persistence and Redis for caching.

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────┐      WebSocket     ┌──────────────┐
│   React     │◄──────────────────►│  Flask API   │
│  Frontend   │                    │   Backend    │
└─────────────┘                    └──────┬───────┘
                                          │
                          ┌───────────────┼───────────────┐
                          │               │               │
                     ┌────▼────┐    ┌─────▼─────┐  ┌─────▼────┐
                     │PostgreSQL│    │   Redis   │  │External  │
                     │ Database │    │   Cache   │  │  APIs    │
                     └──────────┘    └───────────┘  └──────────┘
                                                     • Anthropic
                                                     • Cloudinary
                                                     • Stripe
                                                     • Lulu
```

---

## Architecture Documents

### Overview
➡️ **[Architecture Overview](overview.md)**

- System components
- Technology stack
- Design principles
- Data flow

### Frontend
➡️ **[Frontend Architecture](frontend-architecture.md)**

- React component structure
- State management (TanStack Query)
- Routing and navigation
- UI patterns and components

### Backend
➡️ **[Backend Architecture](backend-architecture.md)**

- Flask application structure
- Service layer patterns
- API design
- Background jobs

### Database
➡️ **[Database Schema](database-schema.md)**

- Entity-relationship diagrams
- Table schemas
- Indexes and constraints
- Migration strategy

---

## Design Principles

### 1. Separation of Concerns
- Frontend handles presentation and user interaction
- Backend handles business logic and data persistence
- External services handle specialized tasks (AI, payments, etc.)

### 2. API-First Design
- RESTful API as the contract between frontend and backend
- API documentation maintained alongside code
- Versioning strategy for breaking changes

### 3. Type Safety
- TypeScript on frontend for compile-time safety
- SQLAlchemy models on backend for runtime validation
- Shared type definitions for API contracts

### 4. Scalability
- Stateless API servers for horizontal scaling
- Redis caching for frequently accessed data
- Database connection pooling
- CDN for static assets

### 5. Security
- HTTPS everywhere
- JWT authentication with refresh tokens
- Input validation and sanitization
- SQL injection prevention (parameterized queries)
- XSS protection

---

## Technology Stack

### Frontend
- **React 19** - UI library
- **TypeScript 5.8** - Type safety
- **Vite 6** - Build tool
- **TanStack Query** - Server state management
- **React Router** - Client-side routing
- **Tailwind CSS** - Styling

### Backend
- **Flask 3.0** - Web framework
- **SQLAlchemy 2.0** - ORM
- **Flask-JWT-Extended** - Authentication
- **Celery** - Background tasks
- **Redis** - Caching and task queue
- **Gunicorn** - WSGI server

### Database
- **PostgreSQL 14+** - Primary database (production)
- **SQLite** - Development database
- **Alembic** - Database migrations

### Infrastructure
- **Render** - Hosting platform
- **Cloudinary** - Image storage
- **Anthropic Claude** - AI recipe extraction
- **Stripe** - Payment processing
- **Lulu** - Print-on-demand

---

## Key Features Architecture

### AI Recipe Extraction
```
User uploads image
       ↓
Cloudinary (storage)
       ↓
Anthropic Claude API (extraction)
       ↓
Backend validation
       ↓
PostgreSQL (save)
```

### Print-on-Demand
```
User creates cookbook
       ↓
PDF generation (backend)
       ↓
Lulu API (print order)
       ↓
Order tracking
```

### Payment Processing
```
User selects plan
       ↓
Stripe Checkout
       ↓
Webhook (backend)
       ↓
Subscription activation
```

---

## See Also

- [Frontend Code Standards](../development/code-standards.md)
- [Backend API Reference](../api/README.md)
- [Database Operations](../operations/database-cli.md)

---

[← Back to Documentation Home](../README.md)
