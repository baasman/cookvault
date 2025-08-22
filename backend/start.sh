#!/bin/bash

# Production startup script for CookVault backend

set -e

echo "Starting CookVault backend..."

# Set default environment variables if not provided
export FLASK_ENV=${FLASK_ENV:-production}
export PORT=${PORT:-8000}
export GUNICORN_WORKERS=${GUNICORN_WORKERS:-4}
export LOG_LEVEL=${LOG_LEVEL:-debug}

# Validate required environment variables
if [[ -z "$SECRET_KEY" ]]; then
    echo "ERROR: SECRET_KEY environment variable is required"
    exit 1
fi

# Set UV to use system Python and ensure it's in PATH
export UV_PYTHON=python
export PATH="/usr/local/bin:/usr/bin:$PATH"

# Check if uv is available and find its location
echo "Checking UV availability..."
UV_PATH=$(which uv 2>/dev/null || echo "/usr/local/bin/uv")
echo "Using UV at: $UV_PATH"

# Debug: Log outgoing IP for Redis allowlist configuration
echo "Checking outgoing IP for Redis allowlist..."
curl -s ipv4.icanhazip.com || echo "Could not determine external IP"

# Create a wrapper function for UV commands
run_uv() {
    if [ -f "$UV_PATH" ]; then
        "$UV_PATH" "$@"
    elif command -v uv >/dev/null 2>&1; then
        uv "$@"
    else
        echo "ERROR: UV not found. Trying with python -m uv..."
        python -m uv "$@"
    fi
}

# Run database migrations
echo "Running database migrations..."

# Check if this is a fresh database or if migrations need to be synced
echo "Checking migration state..."

# First, check if alembic version table exists and has any records
MIGRATION_STATE_CHECK=$(run_uv run python -c "
from app import create_app, db
from sqlalchemy import text
import sys

app = create_app()
with app.app_context():
    try:
        # Check if alembic_version table exists and has records
        result = db.session.execute(text('SELECT version_num FROM alembic_version LIMIT 1')).fetchone()
        if result:
            print('HAS_MIGRATION_STATE')
        else:
            print('NO_MIGRATION_STATE')
    except Exception as e:
        # Table doesn't exist or other error
        print('NO_MIGRATION_STATE')
        sys.exit(0)
" 2>/dev/null)

echo "Migration state check result: $MIGRATION_STATE_CHECK"

if [ "$MIGRATION_STATE_CHECK" = "HAS_MIGRATION_STATE" ]; then
    echo "Migration state found, running upgrade..."
    run_uv run flask db upgrade
else
    echo "No migration state found. Checking if database has existing tables..."

    # Check if ingredient table exists (one of our core tables)
    TABLE_EXISTS_CHECK=$(run_uv run python -c "
from app import create_app, db
from sqlalchemy import text
import sys

app = create_app()
with app.app_context():
    try:
        # Check if ingredient table exists
        result = db.session.execute(text('SELECT 1 FROM ingredient LIMIT 1')).fetchone()
        print('TABLES_EXIST')
    except Exception as e:
        print('TABLES_DO_NOT_EXIST')
        sys.exit(0)
" 2>/dev/null)

    echo "Table existence check result: $TABLE_EXISTS_CHECK"

    if [ "$TABLE_EXISTS_CHECK" = "TABLES_EXIST" ]; then
        echo "Database has existing tables. Marking current migration as applied without running it..."
        run_uv run flask db stamp head
        echo "Migration state synchronized."
    else
        echo "Fresh database detected. Running initial migration..."
        run_uv run flask db upgrade
    fi
fi

# Create logs directory
mkdir -p logs

# Clean up any stale PID file from previous runs
if [ -f /tmp/gunicorn.pid ]; then
    echo "Removing stale PID file..."
    rm -f /tmp/gunicorn.pid
fi

# Start the application with Gunicorn
echo "Starting Gunicorn server on port $PORT with $GUNICORN_WORKERS workers..."

# Find the UV executable for the final exec call
UV_EXEC_PATH=""
if [ -f "$UV_PATH" ]; then
    UV_EXEC_PATH="$UV_PATH"
elif command -v uv >/dev/null 2>&1; then
    UV_EXEC_PATH="uv"
else
    echo "ERROR: Cannot find UV executable for gunicorn startup"
    exit 1
fi

exec "$UV_EXEC_PATH" run gunicorn \
    --config gunicorn.conf.py \
    --bind 0.0.0.0:$PORT \
    --workers $GUNICORN_WORKERS \
    --worker-class sync \
    --preload \
    --access-logfile - \
    --error-logfile - \
    --log-level $LOG_LEVEL \
    wsgi:application