# Gnosis Auth Deployment Guide

This guide covers deploying Gnosis Auth locally and to Google Cloud Run.

## Quick Start

### Local Development

1. **First Time Setup**
   ```bash
   # Copy environment template
   cp .env.example .env
   
   # Edit .env with your settings
   # (The provided .env should work out of the box for local dev)
   ```

2. **Deploy Locally**
   ```bash
   # Simple deployment
   ./scripts/deploy.ps1
   
   # With options
   ./scripts/deploy.ps1 -Target local -Rebuild -Logs
   ```

3. **Access Services**
   - Auth API: http://localhost:5000
   - API Docs: http://localhost:5000/docs (dev mode only)
   - NDB Emulator: http://localhost:8089

### Cloud Run Deployment

1. **Setup Google Cloud**
   ```bash
   # Install gcloud CLI if not already installed
   # https://cloud.google.com/sdk/docs/install
   
   # Authenticate
   gcloud auth login
   gcloud auth configure-docker us-central1-docker.pkg.dev
   ```

2. **Configure Environment**
   ```bash
   # Copy and edit Cloud Run config
   cp .env.cloudrun .env.staging
   # Edit .env.staging with your GCP project details
   ```

3. **Deploy to Staging**
   ```bash
   ./scripts/deploy.ps1 -Target staging
   ```

4. **Deploy to Production**
   ```bash
   # Create production config
   cp .env.staging .env.production
   # Edit with production values
   
   # Deploy
   ./scripts/deploy.ps1 -Target production
   ```

## Deployment Options

### Script Parameters

- `-Target`: Deployment target (local, staging, production, cloudrun)
- `-Tag`: Docker image tag (default: latest)
- `-Rebuild`: Force rebuild with --no-cache
- `-SkipBuild`: Skip Docker build step
- `-Logs`: Show logs after deployment (local only)
- `-WhatIf`: Preview deployment without executing
- `-Help`: Show help message

### Examples

```bash
# Local development with rebuild
./scripts/deploy.ps1 -Target local -Rebuild

# Deploy to staging with specific tag
./scripts/deploy.ps1 -Target staging -Tag v1.0.0

# Production deployment (skip build if image exists)
./scripts/deploy.ps1 -Target production -SkipBuild

# Preview what would happen
./scripts/deploy.ps1 -Target staging -WhatIf
```

## Environment Configuration

### Key Environment Variables

**Application Settings:**
- `APP_NAME`: Application name
- `APP_DOMAIN`: Full domain URL
- `ENVIRONMENT`: development/staging/production
- `SECRET_KEY`: Session secret key
- `JWT_SECRET_KEY`: JWT signing key

**Storage:**
- `GNOSIS_AUTH_STORAGE_PATH`: Local storage path
- `USE_CLOUD_STORAGE`: Enable GCS (true/false)
- `GCS_BUCKET_NAME`: GCS bucket name

**Google Cloud:**
- `PROJECT_ID`: GCP project ID
- `GOOGLE_CLOUD_PROJECT`: Project for NDB
- `GCP_SERVICE_ACCOUNT`: Service account email
- `REGION`: Deployment region

### Creating Secure Keys

```bash
# Generate secret keys
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Or using OpenSSL
openssl rand -base64 32
```

## Docker Architecture

### Services

1. **auth**: Main FastAPI application
   - Port: 5000
   - Auto-reload in development
   - Health checks enabled

2. **ndb-emulator**: Google Datastore emulator (dev only)
   - Port: 8089
   - For local NDB testing

### Volumes

- `./storage:/data`: Persistent application data
- `./:/app`: Live code reload (dev only)

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Stop existing containers
   docker-compose down
   
   # Or find and kill process
   netstat -ano | findstr :5000
   taskkill /F /PID <PID>
   ```

2. **Docker Build Fails**
   ```bash
   # Clean rebuild
   docker system prune -a
   ./scripts/deploy.ps1 -Rebuild
   ```

3. **Cloud Run Permission Errors**
   ```bash
   # Ensure service account has required roles:
   # - Cloud Run Admin
   # - Storage Admin
   # - Artifact Registry Writer
   ```

4. **Environment Variables Not Loading**
   - Check .env file format (KEY=value)
   - No spaces around = sign
   - Remove quotes unless value contains spaces

### Logs

```bash
# Local logs
docker-compose logs -f auth

# Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=gnosis-auth-staging" --limit 50

# Or use Cloud Console
# https://console.cloud.google.com/logs
```

## Production Checklist

- [ ] Generate new SECRET_KEY and JWT_SECRET_KEY
- [ ] Configure Cloud Storage bucket
- [ ] Configure custom domain
- [ ] Enable HTTPS only
- [ ] Set up monitoring/alerting
- [ ] Configure backup strategy
- [ ] Review security settings
- [ ] Set appropriate resource limits
- [ ] Configure auto-scaling parameters

## FastAPI vs Quart

This project uses **FastAPI** instead of Quart because:
- Better performance (Starlette + Pydantic)
- Built-in OpenAPI documentation
- Better type hints and validation
- Larger ecosystem and community
- Native dependency injection
- Better async/await support

Both are good choices, but FastAPI is generally faster and more feature-rich for API services.
