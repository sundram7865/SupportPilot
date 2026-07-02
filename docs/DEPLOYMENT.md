# SupportPilot Deployment Guide

## 1. Recommended Production Architecture

```txt
Frontend:        Vercel
Backend API:     Render/Railway Web Service
Worker:          Render/Railway Background Worker
Celery Beat:     Render/Railway Background Worker
Database:        Neon/Supabase PostgreSQL + pgvector
Redis:           Upstash/managed Redis
Auth:            Clerk
AI:              Gemini
Mock API:        UrbanKart mock API deployed separately
```

## 2. Backend API

Root:

```txt
apps/api
```

Dockerfile:

```txt
apps/api/Dockerfile
```

Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Healthcheck:

```txt
/ready
```

## 3. Backend Environment Variables

```env
ENVIRONMENT=production
DEV_AUTH_ENABLED=false
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require
REDIS_URL=rediss://default:PASSWORD@HOST:6379
CELERY_BROKER_URL=rediss://default:PASSWORD@HOST:6379
CELERY_RESULT_BACKEND=rediss://default:PASSWORD@HOST:6379
URBANKART_BASE_URL=https://your-urbankart-mock-api-domain
URBANKART_API_KEY=your-demo-key
CLERK_ISSUER=https://your-clerk-domain
CLERK_JWKS_URL=https://your-clerk-domain/.well-known/jwks.json
INTEGRATION_SECRET_KEY=your-fernet-key
AI_PROVIDER=gemini
GEMINI_API_KEY=your-rotated-gemini-key
GEMINI_MODEL=gemini-1.5-flash
CORS_ALLOWED_ORIGINS=https://your-vercel-domain.vercel.app
RATE_LIMIT_ENABLED=true
PUBLIC_READ_RATE_LIMIT_PER_MINUTE=60
PUBLIC_WRITE_RATE_LIMIT_PER_MINUTE=10
EXTERNAL_API_RATE_LIMIT_PER_MINUTE=30
```

Do not deploy with:

```txt
DEV_AUTH_ENABLED=true
localhost CORS origins
wildcard CORS
real secrets committed to Git
old exposed API keys
```

## 4. Database Migration

```bash
alembic upgrade head
```

Verify:

```bash
alembic current
alembic heads
```

Verify pgvector:

```sql
select extname from pg_extension where extname='vector';
```

## 5. Celery Worker

```bash
celery -A app.worker.celery_app.celery_app worker --loglevel=info
```

## 6. Celery Beat

```bash
celery -A app.worker.celery_app.celery_app beat --loglevel=info
```

Only one celery-beat instance should run in production.

## 7. Frontend Deployment

Platform:

```txt
Vercel
```

Root:

```txt
apps/web
```

Build:

```bash
npm run build
```

Frontend env:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-api-domain.com
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your-clerk-publishable-key
CLERK_SECRET_KEY=your-clerk-secret-key
```

## 8. Git Safety

```bash
git status
git ls-files | findstr ".env"
```

Allowed:

```txt
.env.example
apps/api/.env.example
apps/web/.env.example
```

Not allowed:

```txt
.env
.env.local
apps/api/.env
apps/web/.env.local
```
