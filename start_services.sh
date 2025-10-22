#!/bin/bash
# Start all restructured services

echo "🚀 Starting OpenAct FraudOps Services..."

# Start score service
echo "Starting score-svc on port 8002..."
cd services/score-svc
uvicorn app.main:app --reload --port 8002 &
SCORE_PID=$!

# Start decision service  
echo "Starting decision-svc on port 8003..."
cd ../decision-svc
uvicorn app.main:app --reload --port 8003 &
DECISION_PID=$!

# Start case service
echo "Starting case-svc on port 8004..."
cd ../case-svc
uvicorn app.main:app --reload --port 8004 &
CASE_PID=$!

cd ../..

echo "✅ All services started!"
echo "Score Service: http://localhost:8002"
echo "Decision Service: http://localhost:8003" 
echo "Case Service: http://localhost:8004"
echo ""
echo "Test with: python test_services.py"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "echo 'Stopping services...'; kill $SCORE_PID $DECISION_PID $CASE_PID; exit" INT
wait
