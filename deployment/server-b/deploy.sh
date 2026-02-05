#!/bin/bash

# Server B (Frontend + Analysis Server) Deployment Script
# This script pulls the latest images and restarts containers

set -e

echo "🚀 Starting Server B deployment..."
echo "📍 Server: Frontend + Log Analysis Server"
echo ""

# Navigate to deployment directory
cd "$(dirname "$0")"

# Pull latest images from Docker Hub
echo "📥 Pulling latest images..."
docker compose pull

# Stop and remove old containers
echo "🛑 Stopping old containers..."
docker compose down

# Start new containers
echo "✅ Starting new containers..."
docker compose up -d

# Wait for health checks
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check container status
echo ""
echo "📊 Container Status:"
docker compose ps

# Check logs for any immediate errors
echo ""
echo "📋 Recent logs:"
docker compose logs --tail=20

echo ""
echo "✨ Deployment complete!"
echo "🌐 Frontend: http://13.62.76.208"
echo "🔧 Analysis API: http://13.62.76.208:8001"
