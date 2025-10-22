# Start all restructured services

Write-Host "🚀 Starting OpenAct FraudOps Services..." -ForegroundColor Green

# Start score service
Write-Host "Starting score-svc on port 8002..." -ForegroundColor Yellow
Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--port", "8002" -WorkingDirectory "services/score-svc" -WindowStyle Hidden

# Start decision service  
Write-Host "Starting decision-svc on port 8003..." -ForegroundColor Yellow
Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--port", "8003" -WorkingDirectory "services/decision-svc" -WindowStyle Hidden

# Start case service
Write-Host "Starting case-svc on port 8004..." -ForegroundColor Yellow
Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--port", "8004" -WorkingDirectory "services/case-svc" -WindowStyle Hidden

Write-Host "✅ All services started!" -ForegroundColor Green
Write-Host "Score Service: http://localhost:8002" -ForegroundColor Cyan
Write-Host "Decision Service: http://localhost:8003" -ForegroundColor Cyan
Write-Host "Case Service: http://localhost:8004" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test with: python test_services.py" -ForegroundColor Magenta
Write-Host ""
Write-Host "Services are running in background. Check Task Manager to stop them." -ForegroundColor Yellow
