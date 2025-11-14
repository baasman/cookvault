#!/bin/bash

# Quick start script for ngrok setup

set -e

echo "🚀 Starting Cookbook Creator with Ngrok HTTPS..."

# Check if .env.ngrok.local exists
if [ ! -f .env.ngrok.local ]; then
    echo "📝 Creating .env.ngrok.local from template..."
    cp .env.ngrok .env.ngrok.local
    echo "⚠️  Please edit .env.ngrok.local and add your NGROK_AUTHTOKEN"
    echo "   Get your token from: https://dashboard.ngrok.com/get-started/your-authtoken"
    echo "   Then run this script again."
    exit 1
fi

# Check if NGROK_AUTHTOKEN is set
if ! grep -q "NGROK_AUTHTOKEN=.*[^your-ngrok-auth-token-here]" .env.ngrok.local; then
    echo "⚠️  Please set your NGROK_AUTHTOKEN in .env.ngrok.local"
    echo "   Get your token from: https://dashboard.ngrok.com/get-started/your-authtoken"
    exit 1
fi

echo "🐳 Starting Docker containers..."
docker compose -f docker-compose.ngrok.yml --env-file .env.ngrok.local up --build -d

echo "⏳ Waiting for services to start..."
sleep 10

echo "🌐 Getting ngrok URLs..."
echo ""
echo "📊 Ngrok Dashboards:"
echo "   Backend:  http://localhost:4040"
echo "   Frontend: http://localhost:4041"
echo ""
echo "🔗 Copy the HTTPS URLs from the dashboards above and update .env.ngrok.local"
echo "   Then restart the frontend: docker compose -f docker-compose.ngrok.yml restart frontend"
echo ""
echo "✅ Setup complete! Access your app via the ngrok HTTPS URLs."