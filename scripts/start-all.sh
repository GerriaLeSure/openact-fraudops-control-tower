#!/bin/bash

# Start all fraud operations services

echo "Starting FraudOps Control Tower services..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Start infrastructure services
echo "Starting infrastructure services..."
docker-compose -f infra/docker-compose.yml up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 30

# Check service health
echo "Checking service health..."
services=(
    "http://localhost:8080/health"  # Gateway
    "http://localhost:8001/health"  # Ingest
    "http://localhost:8002/health"  # Feature
    "http://localhost:8003/health"  # Score
    "http://localhost:8004/health"  # Decision
    "http://localhost:8005/health"  # Case
    "http://localhost:8006/health"  # Audit
    "http://localhost:8007/health"  # Model Monitor
    "http://localhost:8008/health"  # Summary
)

for service in "${services[@]}"; do
    echo "Checking $service..."
    if curl -s "$service" > /dev/null; then
        echo "✅ $service is healthy"
    else
        echo "❌ $service is not responding"
    fi
done

echo ""
echo "FraudOps Control Tower is starting up!"
echo ""
echo "Services:"
echo "- API Gateway: http://localhost:8080"
echo "- Analyst UI: http://localhost:3000"
echo "- Grafana: http://localhost:3001 (admin/admin)"
echo "- Kibana: http://localhost:5601"
echo "- MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
echo ""
echo "To view logs: docker-compose -f infra/docker-compose.yml logs -f"
echo "To stop: docker-compose -f infra/docker-compose.yml down"
