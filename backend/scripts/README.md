# Scripts Directory

This directory contains utility scripts for testing and development.

## Available Scripts

### test_upload.py

A comprehensive test script that demonstrates how to interact with the Flask application using the test client.

**Features:**
- Tests recipe CRUD operations
- Tests file upload functionality
- Tests processing job status checking
- Creates sample data for testing
- Uses Flask test client (no need for running server)

**Usage:**
```bash
# From the backend directory
python scripts/test_upload.py

# Or using uv
uv run python scripts/test_upload.py
```

**What it does:**
1. Creates a Flask app instance in development mode
2. Sets up an in-memory database
3. Tests basic recipe operations (create, read)
4. Tests image upload with a minimal PNG file
5. Checks processing job status
6. Displays all responses for debugging

This script is useful for:
- Testing the API without manual requests
- Debugging upload functionality
- Verifying database operations
- Development and testing workflows