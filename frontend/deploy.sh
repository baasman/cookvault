#!/bin/bash
set -e

echo "🔨 Building CookVault Frontend for production..."

# Clean and install dependencies
echo "📦 Installing dependencies..."
npm ci

# Build the application
echo "🏗️  Building application..."
npm run build

# Verify critical files are present
echo "✅ Verifying build output..."
if [ ! -f "dist/index.html" ]; then
    echo "❌ Error: index.html not found in dist/"
    exit 1
fi

if [ ! -f "dist/_redirects" ]; then
    echo "❌ Error: _redirects file not found in dist/"
    exit 1
fi

echo "🎉 Frontend build completed successfully!"
echo "📁 Build output is in: dist/"
echo "🌐 Ready for deployment to production"

# Show build statistics
echo ""
echo "📊 Build Statistics:"
du -sh dist/
echo "Files in dist/:"
ls -la dist/