# Cookbook Creator Backend

Backend API for the Cookbook Creator application - OCR and recipe digitization platform.

## Setup

### Prerequisites
- Python 3.11+
- UV package manager
- Docker & Docker Compose

### Installation

1. Install dependencies:
```bash
uv pip install -e .
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start services with Docker:
```bash
docker-compose up -d
```

4. Initialize database:
```bash
flask db upgrade
```

## Development

### Run locally
```bash
python run.py
```

### Run with Docker
```bash
docker-compose up --build
```

### Database migrations
```bash
flask db migrate -m "Description"
flask db upgrade
```

## API Endpoints

- `GET /health` - Health check
- `POST /api/recipes/upload` - Upload recipe image
- `GET /api/recipes` - List recipes (paginated)
- `GET /api/recipes/{id}` - Get recipe details
- `GET /api/jobs/{id}` - Get processing job status

## Architecture

```
Frontend → Flask API → PostgreSQL
                   → Redis (caching)
                   → OCR Service (Tesseract)
                   → NLP Service (OpenAI)
```