# Production Deployment Checklist

## Pre-Deployment Verification

### 1. Configuration Management
- [ ] Copy `.env.example` to `.env`
- [ ] Generate secure `API_KEY` (min 16 characters)
- [ ] Generate secure `JWT_SECRET` (min 32 characters)
- [ ] Set `DB_PASSWORD` in environment
- [ ] Configure `DATABASE_URL` for production PostgreSQL
- [ ] Set `APP_ENV=production`
- [ ] Verify all required environment variables are set

### 2. Database Setup
- [ ] PostgreSQL instance is running and accessible
- [ ] Database user has appropriate permissions
- [ ] Run initial migration: `alembic upgrade head`
- [ ] Verify database connectivity from application
- [ ] Enable database backups

### 3. Security Hardening
- [ ] All secrets stored in environment variables (not in code)
- [ ] API keys rotated from defaults
- [ ] JWT secrets are cryptographically secure
- [ ] HTTPS/TLS configured for external traffic
- [ ] Firewall rules restrict access to necessary ports only
- [ ] Container runs as non-root user (verified in Dockerfile)

### 4. Observability
- [ ] Structured JSON logging enabled (`LOG_FORMAT=json`)
- [ ] Log aggregation configured (ELK, Loki, etc.)
- [ ] Prometheus metrics endpoint accessible
- [ ] Grafana dashboards imported
- [ ] Alert rules configured for critical metrics
- [ ] Request tracing with X-Request-ID verified

### 5. Health Checks
- [ ] `/health/live` endpoint responds correctly
- [ ] `/health/ready` endpoint verifies dependencies
- [ ] `/health?deep=true` returns component status
- [ ] Kubernetes/container health checks configured
- [ ] Alert on health check failures

### 6. Resource Limits
- [ ] CPU limits configured for containers
- [ ] Memory limits configured for containers
- [ ] Disk space monitoring active
- [ ] Connection pool sizes tuned for expected load
- [ ] Rate limiting configured for API endpoints

### 7. CI/CD Pipeline
- [ ] GitHub Actions workflows enabled
- [ ] Tests pass on main branch
- [ ] Linting passes (flake8, black, mypy)
- [ ] Docker image builds successfully
- [ ] Container scan passes (Trivy)
- [ ] Deployment automation tested

### 8. Backup & Recovery
- [ ] Database backup strategy implemented
- [ ] Backup restoration procedure tested
- [ ] Disaster recovery plan documented
- [ ] RPO/RTO objectives defined

### 9. Performance
- [ ] Load testing completed
- [ ] Response time SLAs defined
- [ ] Database indexes verified
- [ ] Caching strategy implemented if needed
- [ ] CDN configured for static assets (if applicable)

### 10. Documentation
- [ ] API documentation up to date
- [ ] Runbook created for common operations
- [ ] Incident response procedures documented
- [ ] On-call rotation configured

## Deployment Commands

### Development/Staging
```bash
docker-compose -f docker-compose.yml up -d
```

### Production
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Monitoring Stack
```bash
# Start full stack with monitoring
docker-compose -f docker-compose.prod.yml up -d

# Access Grafana: http://localhost:3000 (admin/admin)
# Access Prometheus: http://localhost:9090
```

## Post-Deployment Verification

- [ ] Application starts without errors
- [ ] All health endpoints return healthy
- [ ] API authentication works correctly
- [ ] Database queries execute successfully
- [ ] Logs are being collected
- [ ] Metrics are being scraped
- [ ] Alerts are firing correctly (test alert)
- [ ] No security vulnerabilities in scan results

## Rollback Procedure

If deployment fails:

1. Stop the new deployment:
   ```bash
   docker-compose -f docker-compose.prod.yml down
   ```

2. Restore previous database backup if needed:
   ```bash
   pg_restore -U skills_user -d skills_rag backup.dump
   ```

3. Deploy previous version:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. Investigate logs and fix issues before retrying.

## Contact & Support

- **On-Call**: [Configure your on-call rotation]
- **Incident Channel**: [Configure your incident channel]
- **Runbook Location**: [Link to runbooks]
