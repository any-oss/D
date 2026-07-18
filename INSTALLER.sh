#!/bin/bash
# LiteQueue Production Installer Script
# For Linux servers and Termux (Android)

set -e

echo "🚀 LiteQueue Production Installer"
echo "=================================="

# Configuration
INSTALL_DIR="${INSTALL_DIR:-/opt/litequeue}"
DOCKER_IMAGE="anydockerhub/dcontainer:latest"
CONTAINER_NAME="litequeue"
PORT="${PORT:-8000}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if running as root (required for system install)
check_root() {
    if [ "$EUID" -ne 0 ] && [ -z "$ALLOW_NON_ROOT" ]; then
        log_warn "Not running as root. Some features may be limited."
        log_info "For full installation, run: sudo $0"
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check for Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        echo "Install Docker:"
        echo "  Ubuntu/Debian: curl -fsSL https://get.docker.com | sh"
        echo "  Termux: pkg install docker (requires root)"
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        echo "Start Docker: sudo systemctl start docker"
        exit 1
    fi
    
    log_info "Docker is installed and running"
}

# Create installation directory
create_install_dir() {
    log_info "Creating installation directory: $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
}

# Download configuration files
download_config() {
    log_info "Downloading configuration files..."
    
    # Create .env file
    if [ ! -f ".env" ]; then
        cat > .env << 'ENVEOF'
DATABASE_URL=postgresql://user:password@localhost:5432/litequeue
SECRET_KEY=change-this-to-a-secure-random-string
WORKERS=1
PORT=8000
LOG_LEVEL=info
ENVEOF
        log_warn "Please edit .env file with your configuration"
    else
        log_info ".env file already exists"
    fi
    
    # Create docker-compose.yml
    cat > docker-compose.yml << 'COMPOSEEOF'
version: '3.8'

services:
  app:
    image: anydockerhub/dcontainer:latest
    container_name: litequeue
    restart: unless-stopped
    ports:
      - "${PORT:-8000}:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
      - WORKERS=${WORKERS:-1}
      - LOG_LEVEL=${LOG_LEVEL:-info}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s
    networks:
      - litequeue-network

  # Optional: PostgreSQL database (uncomment if needed)
  # db:
  #   image: postgres:15-alpine
  #   container_name: litequeue-db
  #   restart: unless-stopped
  #   environment:
  #     - POSTGRES_USER=user
  #     - POSTGRES_PASSWORD=password
  #     - POSTGRES_DB=litequeue
  #   volumes:
  #     - postgres_data:/var/lib/postgresql/data
  #   networks:
  #     - litequeue-network

volumes:
  postgres_data:

networks:
  litequeue-network:
    driver: bridge
COMPOSEEOF
    
    log_info "docker-compose.yml created"
}

# Pull Docker image
pull_image() {
    log_info "Pulling Docker image: $DOCKER_IMAGE"
    docker pull "$DOCKER_IMAGE"
}

# Start the application
start_app() {
    log_info "Starting LiteQueue..."
    
    # Load environment variables
    if [ -f ".env" ]; then
        export $(cat .env | grep -v '^#' | xargs)
    fi
    
    # Start with docker-compose
    if command -v docker-compose &> /dev/null; then
        docker-compose up -d
    else
        docker compose up -d
    fi
    
    # Wait for health check
    log_info "Waiting for application to start..."
    sleep 10
    
    # Check status
    if docker ps | grep -q "$CONTAINER_NAME"; then
        log_info "LiteQueue is running!"
        echo ""
        echo "Access the application at: http://localhost:${PORT:-8000}"
        echo "API Documentation: http://localhost:${PORT:-8000}/docs"
        echo "Health Check: http://localhost:${PORT:-8000}/health"
        echo ""
        echo "View logs: docker logs -f $CONTAINER_NAME"
        echo "Stop: docker stop $CONTAINER_NAME"
    else
        log_error "Application failed to start. Check logs:"
        docker logs $CONTAINER_NAME
        exit 1
    fi
}

# Main installation function
main() {
    check_root
    check_prerequisites
    create_install_dir
    download_config
    pull_image
    start_app
    
    echo ""
    log_info "Installation complete!"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env file with your database credentials"
    echo "2. Configure your firewall to allow port ${PORT:-8000}"
    echo "3. Set up SSL/TLS termination (recommended for production)"
    echo "4. Review PRODUCTION_READINESS.md checklist"
    echo ""
}

# Run main function
main "$@"
