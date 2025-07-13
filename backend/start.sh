#!/bin/bash

# Production startup script for Cookbook Creator backend

set -e

echo "Starting Cookbook Creator backend..."

# Set default environment variables if not provided
export FLASK_ENV=${FLASK_ENV:-production}
export PORT=${PORT:-8000}
export GUNICORN_WORKERS=${GUNICORN_WORKERS:-4}
export LOG_LEVEL=${LOG_LEVEL:-info}

# Validate required environment variables
if [[ -z "$SECRET_KEY" ]]; then
    echo "ERROR: SECRET_KEY environment variable is required"
    exit 1
fi

# Run database migrations
echo "Running database migrations..."
python -m flask db upgrade

# Create logs directory
mkdir -p logs

# Start the application with Gunicorn
echo "Starting Gunicorn server on port $PORT with $GUNICORN_WORKERS workers..."
exec gunicorn \
    --config gunicorn.conf.py \
    --bind 0.0.0.0:$PORT \
    --workers $GUNICORN_WORKERS \
    --worker-class sync \
    --timeout 30 \
    --keepalive 2 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --preload \
    --access-logfile - \
    --error-logfile - \
    --log-level $LOG_LEVEL \
    wsgi:application