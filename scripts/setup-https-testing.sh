#!/bin/bash

echo "🔧 Setting up HTTPS local testing environment..."

# Create certificates directory
mkdir -p certs

# Set permissions
chmod 755 certs

# Copy environment file
if [ ! -f .env ]; then
    cp .env.https .env
    echo "✅ Environment file created (.env)"
else
    echo "⚠️  .env file already exists. Compare with .env.https for HTTPS settings."
fi

# Build and start services
echo "🚀 Building and starting HTTPS services..."
docker compose -f docker-compose.https.yml up --build -d

echo ""
echo "🎉 HTTPS testing environment is starting up!"
echo ""
echo "📋 Access URLs:"
echo "   Frontend: https://localhost:3443"
echo "   Backend:  https://localhost:8443"
echo "   API Test: https://localhost:8443/api/auth/debug"
echo ""
echo "⚠️  You'll see security warnings for self-signed certificates."
echo "   Click 'Advanced' → 'Proceed to localhost (unsafe)' in your browser."
echo ""
echo "🔍 To view logs:"
echo "   docker-compose -f docker-compose.https.yml logs -f"
echo ""
echo "🛑 To stop:"
echo "   docker-compose -f docker-compose.https.yml down"