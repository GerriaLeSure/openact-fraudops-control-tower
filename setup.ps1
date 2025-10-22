# OpenAct FraudOps Setup Script
Write-Host "🚀 OpenAct FraudOps Setup" -ForegroundColor Green
Write-Host "=========================" -ForegroundColor Green

# Check if Docker is running
Write-Host "`n🔍 Checking Docker status..." -ForegroundColor Yellow
try {
    docker version | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    Write-Host "   Download from: https://www.docker.com/products/docker-desktop" -ForegroundColor Cyan
    exit 1
}

# Check if .env file exists
Write-Host "`n🔍 Checking environment configuration..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "✅ .env file exists" -ForegroundColor Green
} else {
    Write-Host "⚠️  .env file not found. Creating from example..." -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "✅ Created .env from .env.example" -ForegroundColor Green
    } else {
        Write-Host "❌ .env.example not found. Please create .env file manually." -ForegroundColor Red
        exit 1
    }
}

# Build and start services
Write-Host "`n🏗️  Building and starting services..." -ForegroundColor Yellow
Write-Host "This may take a few minutes on first run..." -ForegroundColor Cyan

try {
    docker compose up --build -d
    Write-Host "✅ Services started successfully!" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to start services. Check Docker logs." -ForegroundColor Red
    exit 1
}

# Wait for services to be ready
Write-Host "`n⏳ Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Test the system
Write-Host "`n🧪 Testing the system..." -ForegroundColor Yellow
try {
    python test_services.py
    Write-Host "✅ System test completed!" -ForegroundColor Green
} catch {
    Write-Host "⚠️  System test failed. Services may still be starting up." -ForegroundColor Yellow
    Write-Host "   Try running 'python test_services.py' again in a few minutes." -ForegroundColor Cyan
}

# Display access information
Write-Host "`n🌐 Access Information:" -ForegroundColor Green
Write-Host "=====================" -ForegroundColor Green
Write-Host "Analyst UI:     http://localhost:5173" -ForegroundColor Cyan
Write-Host "API Gateway:    http://localhost:8001" -ForegroundColor Cyan
Write-Host "Prometheus:     http://localhost:8005/metrics" -ForegroundColor Cyan
Write-Host "MinIO Console:  http://localhost:9001" -ForegroundColor Cyan

Write-Host "`n🔐 Authentication:" -ForegroundColor Green
Write-Host "==================" -ForegroundColor Green
Write-Host "Username formats:" -ForegroundColor Cyan
Write-Host "  analyst:username  → analyst role" -ForegroundColor White
Write-Host "  sup:username      → supervisor role" -ForegroundColor White
Write-Host "  admin:username    → admin role" -ForegroundColor White

Write-Host "`n📋 Useful Commands:" -ForegroundColor Green
Write-Host "===================" -ForegroundColor Green
Write-Host "View logs:      docker compose logs -f" -ForegroundColor Cyan
Write-Host "Stop services:  docker compose down" -ForegroundColor Cyan
Write-Host "Restart:        docker compose restart" -ForegroundColor Cyan
Write-Host "Test system:    python test_services.py" -ForegroundColor Cyan

Write-Host "`n🎉 Setup complete! The OpenAct FraudOps platform is ready." -ForegroundColor Green
