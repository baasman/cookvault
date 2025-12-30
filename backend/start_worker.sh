#!/bin/bash

# Celery worker startup script for CookVault backend
# This script is used by Docker to start the Celery worker process

set -e

echo "=========================================="
echo "Starting CookVault Celery Worker"
echo "=========================================="

# Set default environment variables
export FLASK_ENV=${FLASK_ENV:-production}
export LOG_LEVEL=${LOG_LEVEL:-info}

echo "Environment: $FLASK_ENV"
echo "Log Level: $LOG_LEVEL"

# Validate required environment variables
if [[ -z "$SECRET_KEY" ]]; then
    echo "ERROR: SECRET_KEY environment variable is required"
    exit 1
fi

if [[ -z "$REDIS_URL" ]]; then
    echo "ERROR: REDIS_URL environment variable is required for Celery broker"
    exit 1
fi

if [[ -z "$DATABASE_URL" ]]; then
    echo "ERROR: DATABASE_URL environment variable is required"
    exit 1
fi

echo "Redis URL configured: ${REDIS_URL:0:20}..."
echo "Database URL configured: ${DATABASE_URL:0:20}..."

# Set UV to use system Python
export UV_PYTHON=python
export PATH="/usr/local/bin:/usr/bin:$PATH"

# Check if uv is available
UV_PATH=$(which uv 2>/dev/null || echo "/usr/local/bin/uv")
echo "Using UV at: $UV_PATH"

# Start Celery worker with memory-optimized settings
echo ""
echo "Starting Celery worker with concurrency=1 for memory efficiency..."
echo "Worker flags:"
echo "  --concurrency=1          : Process one task at a time"
echo "  --prefetch-multiplier=1  : Don't prefetch extra tasks"
echo "  --max-tasks-per-child=50 : Restart after 50 tasks to prevent memory leaks"
echo ""

exec "$UV_PATH" run celery -A celery_worker:celery worker \
    --loglevel="$LOG_LEVEL" \
    --concurrency=1 \
    --prefetch-multiplier=1 \
    --max-tasks-per-child=50 \
    --without-gossip \
    --without-mingle \
    --without-heartbeat
