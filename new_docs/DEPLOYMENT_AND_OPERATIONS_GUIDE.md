# Deployment and Operations Guide

## System Requirements

### Minimum Hardware
- **CPU**: 4+ cores (8+ recommended for production)
- **Memory**: 8GB RAM (16GB+ recommended)
- **Storage**: 50GB SSD (100GB+ recommended)
- **Network**: 100Mbps minimum

### Software Requirements
- **OS**: Linux (Ubuntu 20.04+), macOS, or Windows with WSL2
- **Container Runtime**: Docker 20.10+
- **Orchestration**: Kubernetes 1.24+ (optional)
- **Python**: 3.11+
- **Node.js**: 18+

## Pre-Deployment Checklist

### Security
- [ ] Generate SSL/TLS certificates
- [ ] Configure firewall rules
- [ ] Setup VPC/network isolation
- [ ] Configure secret management system
- [ ] Enable audit logging
- [ ] Review security group rules

### Infrastructure
- [ ] Allocate cloud resources
- [ ] Configure DNS records
- [ ] Setup load balancer
- [ ] Configure auto-scaling policies
- [ ] Setup backup infrastructure
- [ ] Configure monitoring agents

## Local Development Setup

### Backend
\\\ash
git clone <repo-url>
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
docker run -d -p 27017:27017 mongo:latest
docker run -d -p 6379:6379 redis:latest
cp .env.example .env
uvicorn app.main:app --reload
\\\

### Frontend
\\\ash
cd frontend
npm install
cp .env.example .env
npm run dev
\\\

## Docker Deployment

### Docker Compose
\\\ash
docker-compose up -d
docker-compose logs -f
docker-compose down
\\\

### Build Commands
\\\ash
docker build -t caps-backend:latest ./backend
docker build -t caps-frontend:latest ./frontend
docker compose up -d
\\\

## Kubernetes Deployment

### Setup
\\\ash
kubectl create namespace caps
kubectl create secret generic app-secrets -n caps
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/mongodb.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/frontend.yaml
kubectl apply -f k8s/ingress.yaml
\\\

### Verify
\\\ash
kubectl get pods -n caps
kubectl get services -n caps
kubectl get ingress -n caps
\\\

## Configuration Management

### Backend Environment Variables
- DATABASE_URL: MongoDB connection string
- REDIS_URL: Redis connection string
- JWT_SECRET: Secret key for JWT signing
- ENVIRONMENT: production/staging/development
- LOG_LEVEL: info/debug/warn/error
- CORS_ORIGINS: Allowed origins
- ENCRYPTION_KEY: Field-level encryption key

### Frontend Environment Variables
- VITE_API_URL: Backend API endpoint
- VITE_ENVIRONMENT: Environment name
- VITE_LOG_LEVEL: Logging level
- VITE_ENABLE_ANALYTICS: Enable analytics

## Security Hardening

### TLS/SSL
- Use TLS 1.3 minimum
- Install valid SSL certificates
- Enable HSTS headers
- Configure secure cookies

### Network Security
- Firewall: Allow only 80, 443
- VPC: Isolate backend/database
- WAF: Enable for public endpoints
- DDoS: Use managed DDoS protection

### Application Security
- Rate limiting: 100 req/sec per IP
- CORS: Restrict to known origins
- Headers: Add security headers
- HTTPS redirect: Force HTTPS

## Monitoring and Logging

### Prometheus Metrics
- Request latency (p50, p95, p99)
- Error rates (4xx, 5xx)
- Database query performance
- Redis cache hit rates

### ELK Stack
- Elasticsearch: Log storage
- Logstash: Log processing
- Kibana: Log visualization

### Key Alerts
- Error rate > 5% → Critical
- Latency p95 > 500ms → Warning
- Database CPU > 80% → Critical
- Memory usage > 85% → Warning

## Backup and Recovery

### MongoDB Backup
\\\ash
mongodump --uri "mongodb://user:pass@host:27017/caps" --out /backups/
0 2 * * * /usr/local/bin/backup-mongo.sh
\\\

### RTO/RPO Targets
- **RTO**: < 4 hours
- **RPO**: < 1 hour

### Restore
\\\ash
mongorestore --uri "mongodb://user:pass@host:27017" /backups/backup_date
\\\

## Troubleshooting

### Backend Won't Start
\\\ash
docker logs backend
kubectl logs deployment/backend -n caps
telnet localhost 27017
\\\

### High Latency
\\\ash
mongostat
redis-cli info stats
kubectl top pods -n caps
\\\

### Authentication Failures
\\\ash
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/api/health
kubectl get secret app-secrets -n caps -o yaml
\\\

### Database Connection Errors
\\\ash
nc -zv database-host 27017
redis-cli ping
\\\

### Memory Leaks
\\\ash
kubectl top nodes
docker stats
\\\

### Rate Limiting Issues
\\\ash
redis-cli KEYS "rate_limit:*"
redis-cli TTL "rate_limit:user_123"
\\\

## Performance Tuning

### Database
- Create indexes on frequently queried fields
- Monitor slow queries (> 100ms)
- Optimize aggregation pipelines
- Configure connection pooling (max 100)

### Cache Strategy
- Redis for sessions (TTL: 24h)
- Query result caching (TTL: 5m)
- CDN for static assets (TTL: 1y)
- Browser caching for assets

### Load Balancing
- Round-robin across 3+ backend replicas
- Health checks every 10 seconds
- Connection draining 30 seconds
- Session persistence enabled

## Maintenance Windows

### Schedule
- No weekly downtime
- Monthly maintenance: Tuesday 2 AM UTC (if needed)
- Quarterly updates: Major security patches

### Update Procedure
1. Test in staging environment (48h)
2. Create full database backup
3. Schedule maintenance window
4. Apply updates during low-traffic
5. Monitor for 1 hour post-update
6. Have rollback plan ready

## Emergency Procedures

### System Failure
1. Assess root cause
2. Activate failover systems
3. Restore from latest backup
4. Verify data integrity
5. Post-incident review

### Security Incident
1. Isolate affected systems
2. Preserve logs and evidence
3. Notify security team
4. Deploy remediation
5. Internal post-mortem
6. Customer communication

## Performance Targets

- API Response: <200ms (p95)
- Database Query: <100ms (p95)
- Frontend Load: <2 seconds
- Concurrent Users: 10,000+
- Availability: 99.9%
