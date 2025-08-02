#!/bin/bash

echo "🚀 Deploying Redis-Based Parallel Multi-Agent Framework..."

echo "🧹 Stopping old containers..."
docker-compose down

echo "🏗️ Building new framework image..."
docker build -t multi_agent_framework:latest .

echo "🚀 Starting Redis-based multi-agent system..."
docker-compose -f docker-compose.yml up -d

echo "⏳ Waiting for agents to connect to Redis..."
sleep 10

echo "🔍 Checking container status..."
docker-compose -f docker-compose.yml ps

echo "🧪 Testing Redis-based parallel processing..."
docker-compose -f docker-compose.yml exec orchestrator python3 redis_orchestrator.py "Create a three-dimensional model of 50 realistic-looking balls bouncing inside a spinning cube. All code should be contained within a single HTML file. The balls should bounce off the walls of the cube and should be rendered with proper physics to simulate realistic motion. The cube should rotate slowly around its center to provide a dynamic view of the scene." -d

echo ""
echo "✅ Monitor logs:"
echo "docker-compose -f docker-compose.yml logs -f agent-a"
echo "docker-compose -f docker-compose.yml logs -f orchestrator"
echo ""
echo "📊 Check Redis queues:"
echo "redis-cli -h localhost -p 6379 keys 'agent_tasks:*'"
echo "redis-cli -h localhost -p 6379 keys 'result:*'"
