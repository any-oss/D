# LiteQueue - Production Deployment Guide

## Overview
LiteQueue is a production-ready, multi-agent task queue system optimized for deployment on standard servers and mobile devices (Termux).

## Prerequisites

### For Docker Deployment (Recommended)
- Docker Engine 20.10+
- Docker Compose v2.0+ (optional, for local development)
- GitHub Account (for CI/CD)
- Docker Hub Account

### For Termux/Mobile Deployment
- Termux app (Android) or similar terminal emulator
- `pkg install docker` (requires root or Docker-in-Termux setup)
- Minimum 2GB RAM recommended
- ARM64 architecture support

## Quick Start

### 1. Docker Hub Deployment (Automated via GitHub Actions)

The project includes automated CI/CD pipelines that build and push Docker images to Docker Hub.

**Required GitHub Secrets:**
- `DOCKERHUB_USERNAME`: Your Docker Hub username
- `DOCKERHUB_TOKEN`: Docker Hub access token with read/write permissions

**Workflow Triggers:**
- Push to `main` branch → Builds and pushes `anydockerhub/dcontainer:main` and `anydockerhub/dcontainer:latest`
- Version tags (e.g., `v1.2.3`) → Builds and pushes versioned tags
- Pull Requests → Builds but does not push (validation only)

**Supported Platforms:**
- `linux/amd64` (Standard servers, desktops)
- `linux/arm64` (Mobile devices, Raspberry Pi, Apple Silicon)

### 2. Manual Docker Build

```bash
# Build locally
docker build -t anydockerhub/dcontainer:latest .

# Run container
docker run -d \
  --name litequeue \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@localhost:5432/litequeue \
  -e WORKERS=1 \
  anydockerhub/dcontainer:latest
```

### 3. Termux Deployment

```bash
# Install Docker in Termux (requires setup)
pkg update && pkg upgrade
pkg install docker

# Login to Docker Hub
docker login

# Pull the image
docker pull anydockerhub/dcontainer:latest

# Run with minimal resources
docker run -d \
  --name litequeue \
  -p 8000:8000 \
  -e WORKERS=1 \
  -e LOG_LEVEL=info \
  anydockerhub/dcontainer:latest

# Access the application
curl http://localhost:8000/health
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | (required) | PostgreSQL connection string |
| `WORKERS` | `1` | Number of Uvicorn workers (use 1 for mobile) |
| `PORT` | `8000` | Application port |
| `HOST` | `0.0.0.0` | Binding address |
| `LOG_LEVEL` | `info` | Logging level (debug, info, warning, error) |
| `SECRET_KEY` | (required) | Secret key for JWT token generation |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT token expiration time |

### Database Setup

The application uses PostgreSQL with Alembic for migrations. Migrations run automatically on container startup.

```bash
# Example DATABASE_URL format
postgresql://username:password@host:5432/database_name
```

## Health Checks

The container includes built-in health checks:
- Endpoint: `http://localhost:8000/health`
- Interval: 30 seconds
- Timeout: 5 seconds
- Start Period: 15 seconds (optimized for slow mobile CPUs)
- Retries: 2

## Security Features

- **Non-root User**: Container runs as `appuser` (UID 1000)
- **Minimal Base Image**: Alpine Linux for reduced attack surface
- **Automated Scanning**: Trivy scans for vulnerabilities on every build
- **Secrets Management**: No secrets in code; use environment variables or Docker secrets
- **Read-only Filesystem**: Compatible with read-only root filesystem (except /app/data and /app/logs)

## Monitoring

### Prometheus Metrics
Available at: `http://localhost:8000/metrics`

### Application Logs
```bash
# View container logs
docker logs -f litequeue

# Export logs
docker logs litequeue > app.log 2>&1
```

## Troubleshooting

### Container Won't Start
1. Check logs: `docker logs litequeue`
2. Verify database connectivity
3. Ensure required environment variables are set
4. Check resource availability (RAM/CPU)

### Database Migration Failures
```bash
# Run migrations manually inside container
docker exec -it litequeue alembic upgrade head
```

### High Memory Usage (Mobile)
- Reduce workers: `-e WORKERS=1`
- Use lightweight logging: `-e LOG_LEVEL=warning`
- Limit ChromaDB embeddings or disable if not needed

## Development

### Local Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run linting
flake8 api core
mypy api --ignore-missing-imports

# Run tests (if available)
pytest

# Start development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Building for Specific Architectures
```bash
# Build for ARM64 only (mobile)
docker buildx build --platform linux/arm64 -t anydockerhub/dcontainer:arm64 .

# Build multi-architecture
docker buildx build --platform linux/amd64,linux/arm64 \
  -t anydockerhub/dcontainer:latest --push .
```

## CI/CD Pipeline

### Workflows
1. **CI - Lint and Type Check** (`ci.yml`)
   - Runs on PRs and pushes to main
   - Flake8 linting
   - MyPy type checking

2. **CD - Build and Push** (`cd.yml`)
   - Reuses `reusable-docker-build.yml`
   - Multi-platform builds
   - Security scanning with Trivy
   - Pushes to Docker Hub

### Reusable Workflow
The `reusable-docker-build.yml` workflow can be reused in other projects:
```yaml
jobs:
  build:
    uses: ./.github/workflows/reusable-docker-build.yml
    secrets: inherit
    with:
      registry: docker.io
      image_name: your-username/your-repo
      platforms: linux/amd64,linux/arm64
      push: true
      scan_image: true
```

## License
[Add your license information here]

## Support
For issues and feature requests, please open a GitHub issue.
