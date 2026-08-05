# Deployment Guide: Clip Generation Pipeline

Complete guide for deploying the clip generation pipeline to production with Railway, Docker, and environment configuration.

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Local Development Setup](#local-development-setup)
3. [Docker Configuration](#docker-configuration)
4. [Railway Deployment](#railway-deployment)
5. [Environment Variables](#environment-variables)
6. [Database Setup](#database-setup)
7. [Monitoring & Observability](#monitoring--observability)
8. [Security Hardening](#security-hardening)
9. [Performance Tuning](#performance-tuning)
10. [Load Testing](#load-testing)
11. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

Before deploying to production, verify:

- ✅ All 14 launch tasks completed
- ✅ Unit tests passing (50+ tests)
- ✅ Load testing verified (100+ concurrent moments stable)
- ✅ API documentation complete
- ✅ Environment variables configured
- ✅ Database migrations applied
- ✅ Docker image builds successfully
- ✅ HTTPS/TLS certificate configured
- ✅ Rate limiting tested
- ✅ OWASP #1 access control verified
- ✅ Monitoring dashboard operational
- ✅ Error logging and alerting configured

**Pre-deployment verification command**:
```bash
# Run unit tests
pytest backend/tests/ -m unit --cov=backend

# Run smoke tests
pytest backend/tests/ -m smoke

# Verify all dependencies
pip list | grep -E "pytest|locust|sqlalchemy|fastapi"

# Check Docker build
docker build -t clip-pipeline:latest .

# Validate environment config
python -c "from backend.config import settings; print(settings)"
```

---

## Local Development Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ (or SQLite for development)
- Redis (optional, for caching)
- Node.js 18+ (for frontend)
- Docker & Docker Compose
- Git

### Installation

1. **Clone repository**:
```bash
git clone https://github.com/MATTHEWSJARREL/KAZUMEE.git
cd KAZUMEE
```

2. **Create virtual environment**:
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
pip install -r requirements-test.txt  # For testing
```

4. **Setup local database**:
```bash
# SQLite (development)
python -c "from backend.db import models; models.Base.metadata.create_all(bind=engine)"

# Or PostgreSQL
psql -U postgres -c "CREATE DATABASE kazumi_dev;"
export DATABASE_URL="postgresql://user:password@localhost:5432/kazumi_dev"
python -m alembic upgrade head
```

5. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with local settings
```

6. **Start backend**:
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

7. **Start frontend** (in separate terminal):
```bash
cd frontend/web
npm install
npm run dev
```

**Verify local setup**:
```bash
curl http://localhost:8000/api/monitoring/health
```

---

## Docker Configuration

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/monitoring/health')"

# Start application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Build and Test Locally

```bash
# Build Docker image
docker build -t clip-pipeline:latest .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=sqlite:///./test.db \
  -e ENVIRONMENT=development \
  clip-pipeline:latest

# Test container
curl http://localhost:8000/api/monitoring/health
```

### Docker Compose (for local development)

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://kazumi:password@db:5432/kazumi
      ENVIRONMENT: development
      DEBUG: "true"
    depends_on:
      - db
    volumes:
      - ./backend:/app/backend

  frontend:
    build: ./frontend/web
    ports:
      - "3000:3000"
    environment:
      REACT_APP_API_URL: http://localhost:8000

  db:
    image: postgres:14
    environment:
      POSTGRES_USER: kazumi
      POSTGRES_PASSWORD: password
      POSTGRES_DB: kazumi
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

**Run with Compose**:
```bash
docker-compose up -d
docker-compose logs -f backend
```

---

## Railway Deployment

### Prerequisites

- Railway account (https://railway.app)
- GitHub repository connected to Railway
- Docker registry credentials (optional)

### Setup Steps

1. **Connect GitHub repository**:
   - Go to Railway dashboard
   - Click "New Project"
   - Select GitHub repository
   - Authorize Railway access

2. **Configure environment**:
   - In Railway project settings, add environment variables (see [Environment Variables](#environment-variables))
   - Set `ENVIRONMENT=production`

3. **Database setup**:
   - Add PostgreSQL plugin in Railway
   - Copy `DATABASE_URL` from plugin settings
   - Add to environment variables

4. **Deploy**:
   - Railway auto-deploys on `main` branch push
   - Monitor deployment in Railway dashboard
   - Check logs: `railway logs`

5. **Verify deployment**:
```bash
curl https://your-railway-domain.com/api/monitoring/health
```

### Railway Configuration File

Create `railway.json`:

```json
{
  "build": {
    "builder": "dockerfile",
    "dockerfile": "Dockerfile"
  },
  "deploy": {
    "startCommand": "uvicorn backend.main:app --host 0.0.0.0 --port $PORT",
    "healthchecks": {
      "readiness": {
        "command": "curl -f http://localhost:$PORT/api/monitoring/health || exit 1"
      }
    }
  }
}
```

### Auto-scaling Configuration

In Railway project settings:

```yaml
scaling:
  min_replicas: 2
  max_replicas: 10
  target_cpu_percent: 70
  target_memory_percent: 80
  scale_down_delay: 300
  scale_up_delay: 60
```

### Railway CLI Commands

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link to project
railway link

# Deploy
railway up

# View logs
railway logs

# Check status
railway status

# View environment variables
railway variables
```

---

## Environment Variables

### Required Variables

```bash
# Core Configuration
ENVIRONMENT=production  # development, staging, production
DEBUG=false

# Database
DATABASE_URL=postgresql://user:password@host:5432/kazumi
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_RECYCLE=3600

# Authentication
SECRET_KEY=your-super-secret-key-min-32-chars
TOKEN_EXPIRY_HOURS=24

# API Configuration
API_TITLE=Clip Generation Pipeline
API_VERSION=1.0.0
API_DESCRIPTION=Production-ready clip generation API

# CORS Configuration (comma-separated)
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Security
HTTPS_ONLY=true
HSTS_MAX_AGE=31536000

# Rate Limiting (requests per minute)
RATE_LIMIT_AUTH=5
RATE_LIMIT_DETECT=1000
RATE_LIMIT_CLIPS=200
RATE_LIMIT_MONITORING=100

# Storage
STORAGE_PATH=/storage  # or S3 bucket path
STORAGE_BACKEND=local  # local or s3

# S3 Configuration (if using S3)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-bucket-name

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json  # json or text
MAX_LOG_SIZE_MB=100
LOG_RETENTION_DAYS=30

# Monitoring
SENTRY_DSN=https://key@sentry.io/project-id  # Error tracking
DATADOG_API_KEY=your-datadog-key  # Optional
DATADOG_SITE=datadoghq.com

# Video Processing
VIDEO_EXTRACTION_TIMEOUT=300
VIDEO_MAX_SIZE_MB=2000
SUPPORTED_FORMATS=mp4,webm,mov

# Feature Flags
ENABLE_AUTO_CLIP_DETECTION=true
ENABLE_AUTO_EXPORT=false
ENABLE_ANALYTICS=true

# Backup Configuration
BACKUP_ENABLED=true
BACKUP_SCHEDULE=0 2 * * *  # 2 AM daily
BACKUP_RETENTION_DAYS=30
```

### Environment-Specific Files

Create separate `.env` files:

```bash
# .env.development
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=sqlite:///./test.db
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# .env.staging
ENVIRONMENT=staging
DEBUG=false
DATABASE_URL=postgresql://user:pass@staging-db:5432/kazumi
CORS_ORIGINS=https://staging.yourdomain.com

# .env.production
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql://user:pass@prod-db:5432/kazumi
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### Loading Environment Variables

```python
# backend/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    DATABASE_URL: str = "sqlite:///./test.db"
    SECRET_KEY: str
    
    class Config:
        env_file = f".env.{os.getenv('ENVIRONMENT', 'development')}"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
```

---

## Database Setup

### PostgreSQL (Production)

1. **Create database**:
```bash
psql -U postgres
CREATE DATABASE kazumi;
CREATE USER kazumi_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE kazumi TO kazumi_user;
```

2. **Apply migrations**:
```bash
export DATABASE_URL="postgresql://kazumi_user:secure_password@localhost:5432/kazumi"
python -m alembic upgrade head
```

3. **Create indexes** (auto-created on app startup):
```bash
# Manually create if needed
python -c "from backend.database.migrations.add_clip_indexes import upgrade; upgrade()"
```

4. **Backup strategy**:
```bash
# Daily backup
pg_dump kazumi > /backups/kazumi_$(date +%Y%m%d).sql

# Restore from backup
psql kazumi < /backups/kazumi_20260805.sql

# Continuous WAL archiving (in postgresql.conf)
wal_level = replica
archive_mode = on
archive_command = 'cp %p /backups/wal_archive/%f'
```

### Database Connection Pooling

Use connection pooling for performance:

```python
# backend/database/engine.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_recycle=3600,  # Recycle connections every hour
    pool_pre_ping=True,  # Verify connections before use
)
```

---

## Monitoring & Observability

### Health Checks

Implement readiness and liveness probes:

```python
# backend/routes/health.py
@app.get("/health/live")  # Kubernetes liveness probe
async def liveness():
    return {"status": "alive"}

@app.get("/health/ready")  # Kubernetes readiness probe
async def readiness(db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        return {"status": "ready"}
    except:
        return {"status": "not_ready"}, 503
```

### Logging Configuration

```python
# backend/core/logging.py
import logging
import json
from pythonjsonlogger import jsonlogger

# JSON structured logging for production
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Log all requests
@app.middleware("http")
async def log_requests(request, call_next):
    logger.info({
        "method": request.method,
        "path": request.url.path,
        "client": request.client.host,
        "timestamp": datetime.utcnow().isoformat()
    })
    response = await call_next(request)
    return response
```

### Metrics Collection

```python
# backend/core/metrics.py
from prometheus_client import Counter, Histogram

request_count = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint']
)

clip_creation_total = Counter(
    'clip_creation_total',
    'Total clips created',
    ['status']  # success, failed
)

extraction_duration = Histogram(
    'extraction_duration_seconds',
    'Video extraction duration'
)
```

### External Monitoring Services

#### Sentry (Error Tracking)
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,
    environment=os.getenv("ENVIRONMENT")
)
```

#### Datadog (APM)
```python
from ddtrace import patch_all, config

patch_all()
config.fastapi['distributed_tracing'] = True
```

#### Grafana/Prometheus
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'clip-pipeline'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

---

## Security Hardening

### HTTPS/TLS

Force HTTPS in production:

```python
# backend/security_middleware.py
@app.middleware("http")
async def force_https(request, call_next):
    if request.url.scheme == "http" and settings.ENVIRONMENT == "production":
        return RedirectResponse(
            url=request.url.replace(scheme="https"),
            status_code=301
        )
    return await call_next(request)
```

### Security Headers

```python
# Configured in backend/security_middleware.py
security_headers = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
}
```

### Rate Limiting

Configure endpoint-specific rate limits:

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/auth/login")
@limiter.limit("5/5minutes")
async def login(request: Request, credentials: LoginRequest):
    pass
```

### CORS Configuration

```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### Database Security

```sql
-- Least privilege user
CREATE USER clip_app WITH PASSWORD 'strong_password';
GRANT CONNECT ON DATABASE kazumi TO clip_app;
GRANT USAGE ON SCHEMA public TO clip_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO clip_app;

-- Row-level security
ALTER TABLE clips ENABLE ROW LEVEL SECURITY;
CREATE POLICY streamer_isolation ON clips
    FOR ALL USING (streamer_id = current_user_id);
```

### Secrets Management

Use Railway secrets or environment variables:

```bash
# Never commit secrets
echo "*.env" >> .gitignore
echo "secrets/" >> .gitignore

# Use Railway CLI
railway variables set DATABASE_URL=postgresql://...
railway variables set SECRET_KEY=your-secret-key
```

---

## Performance Tuning

### Database Query Optimization

Indexes are auto-created on startup:

```python
# backend/database/migrations/add_clip_indexes.py
# Created indexes:
# - clips_status_idx: for clip status filtering
# - clips_created_at_idx: for date-based queries
# - clips_streamer_status_idx: for streamer + status queries
# - clips_streamer_created_idx: for recent clips by streamer
# - clips_status_created_idx: for status + date queries
# - clips_export_status_idx: for export workflows
# - clips_public_created_idx: for public clip feeds
```

**Query performance**: 10-100x faster with indexes.

### Connection Pooling

```python
# Already configured in database engine
pool_size=20           # Min connections
max_overflow=40        # Max additional connections
pool_recycle=3600      # Recycle stale connections
pool_pre_ping=True     # Test connections before use
```

### Caching Strategy

```python
from functools import lru_cache
import redis

# In-memory caching for frequently accessed data
@lru_cache(maxsize=1000)
def get_clip_by_id(clip_id: int):
    pass

# Redis caching (optional)
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0
)

@app.get("/api/clips/{clip_id}")
async def get_clip(clip_id: int):
    cached = redis_client.get(f"clip:{clip_id}")
    if cached:
        return json.loads(cached)
    
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    redis_client.setex(f"clip:{clip_id}", 3600, json.dumps(clip))
    return clip
```

### API Response Compression

```python
from fastapi.middleware.gzip import GZIPMiddleware

app.add_middleware(GZIPMiddleware, minimum_size=1000)
```

### Async Database Access

Use async SQLAlchemy for better concurrency:

```python
# backend/database/async_engine.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/kazumi",
    echo=False,
    pool_size=20,
    max_overflow=40
)

async def get_async_session():
    async with AsyncSession(engine) as session:
        yield session
```

---

## Load Testing

### Pre-production Load Testing

Run load tests against staging before production deployment:

```bash
# Install dependencies
pip install -r requirements-test.txt

# Normal load (recommended starting point)
locust -f backend/tests/load_test.py \
  --host=https://staging.yourdomain.com \
  -u 100 -r 10 -t 5m \
  --headless \
  --csv=results

# Stress test (500 concurrent users)
locust -f backend/tests/load_test.py \
  --host=https://staging.yourdomain.com \
  -u 500 -r 50 -t 10m \
  --headless

# Spike test (sudden traffic surge)
locust -f backend/tests/load_test.py \
  --host=https://staging.yourdomain.com \
  -u 1000 -r 100 -t 5m \
  --headless
```

### Success Criteria

At 100 concurrent users:
- ✅ Response time p95 < 200ms
- ✅ Success rate > 99%
- ✅ Error rate < 1%
- ✅ RPS > 50 requests/second

**Performance thresholds**:
- ⚠️ p95 > 1000ms: Performance degradation
- 🚨 Error rate > 5%: Potential bottleneck
- 🔴 p99 > 5000ms: System struggling

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors

```
Error: could not connect to server: Connection refused
```

**Solution**:
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Verify DATABASE_URL
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1;"
```

#### 2. Out of Memory

```
MemoryError: Unable to allocate X.XX GiB
```

**Solution**:
```bash
# Increase memory limits in Railway
# Or reduce pool_size/max_overflow

# Check current usage
ps aux | grep python
```

#### 3. Slow Queries

```
Query "SELECT * FROM clips" took 5000ms
```

**Solution**:
```bash
# Check if indexes exist
\d+ clips

# Create missing indexes
python -c "from backend.database.migrations.add_clip_indexes import upgrade; upgrade()"

# Analyze query plan
EXPLAIN ANALYZE SELECT * FROM clips WHERE status = 'pending';
```

#### 4. Rate Limiting Too Aggressive

Increase rate limits in environment variables:

```bash
RATE_LIMIT_DETECT=2000  # Moment detection: 2000/min
RATE_LIMIT_CLIPS=500    # Clip API: 500/min
```

#### 5. CORS Errors

```
Access to XMLHttpRequest blocked by CORS policy
```

**Solution**:
```bash
# Add domain to CORS_ORIGINS
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### Debugging

Enable debug logging:

```bash
# Backend
DEBUG=true
LOG_LEVEL=DEBUG

# View Railway logs
railway logs -f

# Check application logs
curl https://yourdomain.com/api/monitoring/errors

# Enable Sentry
SENTRY_DSN=your-sentry-url
```

### Health Check

Regular production monitoring:

```bash
# Every 5 minutes
curl -s https://yourdomain.com/api/monitoring/health | jq .

# Database connectivity
curl -s https://yourdomain.com/api/monitoring/stats | jq .database

# Check error rate
curl -s https://yourdomain.com/api/monitoring/clip-success-rate | jq .success_rate_percent
```

---

## Post-Deployment

### Immediate Verification

```bash
# 1. API health
curl https://yourdomain.com/api/monitoring/health

# 2. Database connectivity
curl https://yourdomain.com/api/monitoring/stats

# 3. Load test (light)
locust -f backend/tests/load_test.py \
  --host=https://yourdomain.com \
  -u 10 -r 2 -t 2m --headless

# 4. Monitor logs
railway logs -f

# 5. Verify monitoring dashboard
# Open http://yourdomain.com/monitoring in browser
```

### First Week Monitoring

- **Daily**: Check error logs, success rates, storage usage
- **2x Daily**: Monitor response times and database connection pool
- **Real-time**: Set up alerts for error rate > 5% or p95 > 1000ms
- **Weekly**: Review performance metrics, user feedback

### Gradual Rollout

```
Day 1: 10% traffic (canary deployment)
Day 2: 25% traffic
Day 3: 50% traffic
Day 4+: 100% traffic (if all metrics green)
```

---

## Rollback Plan

If deployment fails:

```bash
# View deployment history
railway deployments

# Rollback to previous version
railway deployments rollback <deployment-id>

# Or redeploy from GitHub
railway up  # Re-triggers deployment
```

---

## Maintenance

### Weekly Tasks

```bash
# Backup database
pg_dump kazumi > /backups/kazumi_$(date +%Y%m%d_%H%M%S).sql

# Check disk usage
curl https://yourdomain.com/api/clips/storage/stats | jq .total_size_mb

# Review error logs
curl https://yourdomain.com/api/monitoring/errors | jq '.errors[:10]'
```

### Monthly Tasks

```bash
# Review performance metrics
# - Check p95, p99 response times
# - Verify success rate (should be > 99%)
# - Review slow queries

# Update dependencies
pip list --outdated
pip install --upgrade -r requirements.txt

# Cleanup old logs (retention: 30 days)
# Automated by LOG_RETENTION_DAYS configuration
```

### Quarterly Tasks

```bash
# Security audit
# - Review access logs
# - Check for suspicious activity
# - Update security headers

# Capacity planning
# - Analyze growth trends
# - Plan for scaling
# - Review cost optimization
```

---

## Support & Escalation

### Issue Priority Levels

| Priority | Response Time | Example |
|----------|---|---|
| P0 (Critical) | 15 min | API down, data loss |
| P1 (Urgent) | 1 hour | High error rate (>50%) |
| P2 (High) | 4 hours | Performance degradation |
| P3 (Medium) | 24 hours | Minor bugs, feature requests |

### Escalation Path

1. Check monitoring dashboard and logs
2. Review application health endpoints
3. Consult this troubleshooting guide
4. Check Railway documentation
5. Contact Railway support if infrastructure issue

---

## Additional Resources

- [Railway Documentation](https://docs.railway.app)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [PostgreSQL Administration](https://www.postgresql.org/docs/current/admin.html)
- [API Documentation](./API.md)
- [Testing Guide](./backend/tests/README.md)

---

**Last Updated**: 2026-08-05
**Version**: 1.0.0
**Deployment Status**: Ready for Production ✅
