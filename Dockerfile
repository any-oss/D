# Optimized Dockerfile for Termux/Mobile Deployment
# Single-stage build for simplicity on mobile devices
FROM python:3.11-alpine

WORKDIR /app

# Install minimal runtime dependencies (Alpine for small image size)
RUN apk add --no-cache libffi curl bash

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/ ./api/
COPY core/ ./core/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY main.py ./main.py
COPY entrypoint.sh ./entrypoint.sh

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Create non-root user compatible with mobile runtimes
RUN addgroup -g 1000 appgroup && \
    adduser -u 1000 -G appgroup -D appuser && \
    chown -R appuser:appgroup /app

USER appuser

# Expose port
EXPOSE 8000

# Health check optimized for low-resource devices (Termux/mobile)
# Reduced retries and longer start-period for slower mobile CPUs
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=2 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use entrypoint script for proper initialization
ENTRYPOINT ["/app/entrypoint.sh"]
