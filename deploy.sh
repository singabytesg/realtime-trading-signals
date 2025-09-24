#!/bin/bash

# Deploy script for Real-time Trading Signals Server

set -e

echo "🚀 Deploying Real-time Trading Signals Server..."

# Build and start with Docker Compose
echo "📦 Building Docker image..."
docker-compose build --no-cache

echo "🔄 Starting services..."
docker-compose up -d

echo "⏳ Waiting for service to be healthy..."
timeout 60s bash -c 'until docker-compose ps | grep -q "healthy"; do sleep 2; done' || {
    echo "❌ Service failed to become healthy within 60 seconds"
    echo "📋 Container logs:"
    docker-compose logs
    exit 1
}

echo "✅ Deployment successful!"
echo "🌐 Service available at: http://localhost:8000"
echo "📊 Dashboard: http://localhost:8000/"
echo "📈 API Status: http://localhost:8000/api/status"

echo ""
echo "📋 Useful commands:"
echo "  View logs:     docker-compose logs -f"
echo "  Stop service:  docker-compose down"
echo "  Restart:       docker-compose restart"