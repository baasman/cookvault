"""
WSGI entry point for production deployment
"""
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set environment to production if not already set
if not os.environ.get('FLASK_ENV'):
    os.environ['FLASK_ENV'] = 'production'

from app import create_app

# Create the application instance
application = create_app()

if __name__ == "__main__":
    application.run()