# API Middleware for Team B AI-Agent System

This directory contains middleware components for the FastAPI application.

## Components

- `auth.py` - Authentication middleware providing API key and JWT token support

## Usage

To enable authentication, add the middleware to your FastAPI app in `api/main.py`:

```python
from fastapi import FastAPI
from middleware.auth import auth_middleware

app = FastAPI()

# Add authentication middleware
app.middleware("http")(auth_middleware)
```

## Configuration

Set the following environment variables:

- `TEAM_B_API_KEY` - Your API key (default: "dev-api-key-change-in-production")
- `TEAM_B_JWT_SECRET` - Secret key for JWT tokens (default: "dev-jwt-secret-change-in-production")

## Security Notice

**Important**: Change the default API key and JWT secret before deploying to production!
