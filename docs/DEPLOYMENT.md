# Deployment Guide

## Quick Start

1. **Prerequisites**
   - Docker and Docker Compose
   - Python 3.11+
   - Node.js 18+ (for UI development)

2. **Environment Setup**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Start All Services**
   ```bash
   ./scripts/start-all.sh
   ```

4. **Access Services**
   - API Gateway: http://localhost:8080
   - Analyst UI: http://localhost:3000
   - Grafana: http://localhost:3001 (admin/admin)
   - Kibana: http://localhost:5601
   - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)

## Service Architecture

### Core Services
- **Gateway** (8080): API gateway with JWT authentication
- **Ingest** (8001): Transaction and claim ingestion
- **Feature** (8002): Real-time feature engineering
- **Score** (8003): Ensemble fraud scoring
- **Decision** (8004): Risk-based decision engine
- **Case** (8005): Case management system
- **Audit** (8006): Immutable audit trail
- **Model Monitor** (8007): Performance monitoring
- **Summary** (8008): Optional event summarization

### Infrastructure
- **Kafka**: Message streaming
- **Redis**: Caching and session storage
- **PostgreSQL**: Configuration and audit metadata
- **MongoDB**: Case management data
- **MinIO**: Evidence storage
- **Prometheus**: Metrics collection
- **Grafana**: Monitoring dashboards
- **ELK Stack**: Logging and search

## Configuration

### Environment Variables
Key configuration options in `.env`:

```bash
# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_DB=fraudops
POSTGRES_USER=fraudops
POSTGRES_PASSWORD=fraudops_password

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production

# Summary Service (Optional)
SUMMARY_PROVIDER=none  # none, openai, azureai
OPENAI_API_KEY=your-openai-key
```

### Default Users
The system comes with default users:
- `admin` / `password` (admin role)
- `supervisor` / `password` (supervisor role)
- `analyst1` / `password` (analyst role)

## Development

### Running Individual Services
```bash
# Start infrastructure only
docker-compose -f infra/docker-compose.yml up -d

# Run individual services
cd services/ingest-svc
pip install -r requirements.txt
python main.py
```

### Frontend Development
```bash
cd ui/web
npm install
npm run dev
```

### Testing
```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Performance tests
python tests/e2e/performance_test.py
```

## Production Deployment

### Docker Deployment
```bash
# Build all services
docker-compose -f infra/docker-compose.yml build

# Deploy with production config
docker-compose -f infra/docker-compose.yml -f docker-compose.prod.yml up -d
```

### Kubernetes Deployment
```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/
```

### Security Considerations
1. Change default passwords and JWT secret
2. Use TLS for all communications
3. Configure proper firewall rules
4. Enable audit logging
5. Regular security updates

## Monitoring

### Health Checks
All services expose health endpoints:
- `GET /health` - Service health status

### Metrics
Prometheus metrics available at:
- `GET /metrics` - Prometheus format metrics

### Logging
Structured JSON logging to stdout, collected by ELK stack.

## Troubleshooting

### Common Issues

1. **Services not starting**
   - Check Docker is running
   - Verify port availability
   - Check service logs: `docker-compose logs <service>`

2. **Database connection errors**
   - Verify database credentials in `.env`
   - Check database is running: `docker-compose ps`

3. **Kafka connection issues**
   - Wait for Kafka to fully start (30-60 seconds)
   - Check Kafka logs: `docker-compose logs kafka`

4. **UI not loading**
   - Verify gateway is running on port 8080
   - Check browser console for errors
   - Verify CORS configuration

### Logs
```bash
# View all logs
docker-compose -f infra/docker-compose.yml logs -f

# View specific service logs
docker-compose -f infra/docker-compose.yml logs -f gateway
```

### Performance Tuning
- Adjust Kafka partitions based on throughput
- Configure Redis memory limits
- Tune database connection pools
- Scale services horizontally as needed

## Backup and Recovery

### Database Backups
```bash
# PostgreSQL backup
docker exec fraudops-postgres pg_dump -U fraudops fraudops > backup.sql

# MongoDB backup
docker exec fraudops-mongo mongodump --db fraudops_cases --out /backup
```

### Evidence Storage
MinIO data is stored in Docker volumes. Backup the volume:
```bash
docker run --rm -v fraudops_minio_data:/data -v $(pwd):/backup alpine tar czf /backup/minio-backup.tar.gz /data
```

## Support

For issues and questions:
1. Check the logs first
2. Review this documentation
3. Check GitHub issues
4. Contact the development team
