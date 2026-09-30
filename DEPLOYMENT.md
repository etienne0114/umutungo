# Umutungo Deployment Guide

## Local Development Setup

### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL database (Supabase recommended)
- Virtual environment

### Backend Setup

1. **Environment Configuration**
   ```bash
   cd apps/api
   cp .env.example .env
   ```

2. **Configure .env file**
   ```env
   AUTH_REQUIRED=false  # Set to false for local development
   DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-0-REGION.pooler.supabase.com:5432/postgres
   SUPABASE_URL=https://your-project-ref.supabase.co
   SUPABASE_SECRET_KEY=your-secret-key
   CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
   ```

3. **Install Dependencies**
   ```bash
   cd apps/api
   source ../../.venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Run Database Migrations**
   ```bash
   alembic upgrade head
   ```

5. **Start Backend Server**
   ```bash
   AUTH_REQUIRED=false python -m uvicorn govasset_api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Frontend Setup

1. **Environment Configuration**
   ```bash
   cd apps/web
   cp .env.example .env.local
   ```

2. **Configure .env.local file**
   ```env
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
   NEXT_PUBLIC_AUTH_REQUIRED=false  # Set to false for local development
   NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
   NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=your-publishable-key
   ```

3. **Install Dependencies**
   ```bash
   cd apps/web
   npm install
   ```

4. **Start Frontend Server**
   ```bash
   npm run dev
   ```

### Quick Start (Production Mode)

Use the provided script to start both services:

```bash
./scripts/start-production.sh
```

This will:
- Start the backend API on port 8000
- Start the frontend on port 3000
- Verify both services are healthy
- Handle graceful shutdown

## Production Deployment

### Backend Deployment

1. **Environment Variables (Production)**
   ```env
   AUTH_REQUIRED=true  # Enable authentication in production
   DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-0-REGION.pooler.supabase.com:5432/postgres
   SUPABASE_URL=https://your-project-ref.supabase.co
   SUPABASE_SECRET_KEY=your-secret-key
   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
   CORS_ORIGINS=https://your-production-domain.com
   CORS_ORIGIN_REGEX=^https://.*\.your-production-domain\.com$
   ```

2. **Deploy to Render/Railway/etc.**
   - Set environment variables in the deployment platform
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn govasset_api.main:app --host 0.0.0.0 --port $PORT`

3. **Database Migration**
   ```bash
   alembic upgrade head
   ```

### Frontend Deployment

1. **Environment Variables (Production)**
   ```env
   NEXT_PUBLIC_API_BASE_URL=https://your-backend-api.com
   NEXT_PUBLIC_AUTH_REQUIRED=true  # Enable authentication in production
   NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
   NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=your-publishable-key
   ```

2. **Deploy to Vercel/Netlify/etc.**
   - Set environment variables in the deployment platform
   - Build command: `npm run build`
   - Output directory: `.next`

### Vercel Deployment (Recommended)

1. **Backend (Render/Railway)**
   - Create a new web service
   - Connect to GitHub repository
   - Set environment variables
   - Deploy

2. **Frontend (Vercel)**
   - Create a new project
   - Connect to GitHub repository
   - Set environment variables
   - Deploy

### Database Setup

1. **Supabase Setup**
   - Create a new Supabase project
   - Get database connection string
   - Get API keys (URL, anon key, service role key)
   - Configure RLS policies if needed

2. **Run Migrations**
   ```bash
   cd apps/api
   alembic upgrade head
   ```

## Verification

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Frontend health
curl http://localhost:3000
```

### API Testing

```bash
# Test assets endpoint
curl http://localhost:8000/api/v1/assets?active=true

# Test triage endpoint
curl http://localhost:8000/api/v1/triage

# Test insights endpoint
curl http://localhost:8000/api/v1/triage-runs/1/insights
```

## Troubleshooting

### Backend Issues

1. **Database Connection Error**
   - Verify DATABASE_URL is correct
   - Check database is accessible
   - Verify SSL certificate

2. **Migration Errors**
   - Check alembic current version: `alembic current`
   - Force stamp if needed: `alembic stamp head`
   - Reset migrations (CAUTION): `alembic downgrade base`

3. **Authentication Errors**
   - Verify SUPABASE_URL and keys
   - Check AUTH_REQUIRED setting
   - Verify CORS configuration

### Frontend Issues

1. **API Connection Error**
   - Verify NEXT_PUBLIC_API_BASE_URL
   - Check backend is running
   - Verify CORS configuration

2. **Build Errors**
   - Clear Next.js cache: `rm -rf .next`
   - Reinstall dependencies: `rm -rf node_modules && npm install`
   - Check TypeScript errors

3. **Authentication Issues**
   - Verify NEXT_PUBLIC_AUTH_REQUIRED matches backend
   - Check Supabase configuration
   - Clear browser cookies/storage

## Security Considerations

1. **Never commit sensitive data**
   - .env files
   - API keys
   - Database credentials

2. **Use environment variables**
   - All secrets in environment variables
   - Different configs for dev/staging/prod

3. **Enable authentication in production**
   - Set AUTH_REQUIRED=true
   - Configure Supabase properly
   - Implement RLS policies

4. **CORS configuration**
   - Restrict to allowed domains
   - Use regex patterns for subdomains
   - Regularly review CORS settings

## Monitoring

### Backend Monitoring
- Health endpoint: `/health`
- Error tracking (Sentry recommended)
- Performance monitoring (APM tools)

### Frontend Monitoring
- Error tracking (Sentry recommended)
- Performance monitoring (Vercel Analytics)
- User analytics (if needed)

## Backup and Recovery

### Database Backups
- Supabase provides automatic backups
- Export data regularly
- Test restore procedures

### Application Backups
- Version control (Git)
- Environment configurations
- Migration files

## Support

For issues or questions:
- Check documentation in `/docs`
- Review error logs
- Check GitHub issues
- Contact development team
