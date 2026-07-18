#!/bin/bash
# =============================================================================
# LiteQueue - One-Click Management Script
# =============================================================================
# Features: install, start, stop, restart, status, logs, backup, restore, 
#           prune, update, uninstall
# Optimized for: Linux Servers, Termux (Android), Raspberry Pi
# =============================================================================

set -e

# Configuration
APP_NAME="litequeue"
CONTAINER_NAME="${APP_NAME}_app"
DB_CONTAINER_NAME="${APP_NAME}_db"
NETWORK_NAME="${APP_NAME}_net"
VOLUME_NAME="${APP_NAME}_data"
BACKUP_VOLUME_NAME="${APP_NAME}_backups"
IMAGE_REPO="anydockerhub/dcontainer"
IMAGE_TAG="latest"
INSTALL_DIR="$HOME/${APP_NAME}"
COMPOSE_FILE="${INSTALL_DIR}/docker-compose.yml"
ENV_FILE="${INSTALL_DIR}/.env"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running in Termux
is_termux() {
    [ -n "$TERMUX_VERSION" ] || [ -d "$PREFIX" ] || grep -q "Android" /proc/version 2>/dev/null
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed."
        if is_termux; then
            log_info "Installing Docker in Termux..."
            pkg update -y && pkg install -y docker
            systemctl start docker 2>/dev/null || dockerd &
        else
            log_info "Installing Docker..."
            curl -fsSL https://get.docker.com | sh
            sudo usermod -aG docker $USER
            log_warn "Please log out and back in to apply group changes."
        fi
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running."
        if is_termux; then
            log_info "Starting Docker daemon in Termux..."
            dockerd &
            sleep 5
        else
            log_info "Starting Docker service..."
            sudo systemctl start docker
        fi
    fi
    log_success "Docker is ready."
}

# Check if Docker Compose is available
check_compose() {
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        log_error "Docker Compose is not installed."
        if is_termux; then
            pkg install -y docker-compose
        else
            sudo apt-get update && sudo apt-get install -y docker-compose-plugin 2>/dev/null || \
            curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && \
            chmod +x /usr/local/bin/docker-compose
        fi
        check_compose # Retry
    fi
    log_success "Docker Compose is ready ($COMPOSE_CMD)."
}

# Generate .env file
generate_env() {
    if [ -f "$ENV_FILE" ]; then
        log_warn ".env file already exists. Skipping generation."
        return
    fi
    
    log_info "Generating .env file..."
    cat > "$ENV_FILE" << ENVEOF
# LiteQueue Environment Configuration
APP_NAME=${APP_NAME}
ENVIRONMENT=production
SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p)
DATABASE_URL=postgresql://litequeue:securepassword123@db:5432/litequeue
REDIS_URL=redis://redis:6379/0
LOG_LEVEL=INFO
WORKERS=1
HOST=0.0.0.0
PORT=8000
ENVEOF
    
    chmod 600 "$ENV_FILE"
    log_success ".env file created at $ENV_FILE"
}

# Generate docker-compose.yml
generate_compose() {
    if [ -f "$COMPOSE_FILE" ]; then
        log_warn "docker-compose.yml already exists. Skipping generation."
        return
    fi
    
    log_info "Generating docker-compose.yml..."
    cat > "$COMPOSE_FILE" << COMPOSEEOF
version: '3.8'

services:
  app:
    image: ${IMAGE_REPO}:${IMAGE_TAG}
    container_name: ${CONTAINER_NAME}
    restart: unless-stopped
    ports:
      - "\${PORT:-8000}:8000"
    environment:
      - DATABASE_URL=\${DATABASE_URL}
      - REDIS_URL=\${REDIS_URL}
      - SECRET_KEY=\${SECRET_KEY}
      - ENVIRONMENT=\${ENVIRONMENT:-production}
      - LOG_LEVEL=\${LOG_LEVEL:-INFO}
      - WORKERS=\${WORKERS:-1}
    volumes:
      - ${VOLUME_NAME}:/app/data
      - ${BACKUP_VOLUME_NAME}:/app/backups
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - ${NETWORK_NAME}

  db:
    image: postgres:15-alpine
    container_name: ${DB_CONTAINER_NAME}
    restart: unless-stopped
    environment:
      POSTGRES_DB: litequeue
      POSTGRES_USER: litequeue
      POSTGRES_PASSWORD: securepassword123
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U litequeue -d litequeue"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - ${NETWORK_NAME}

  redis:
    image: redis:7-alpine
    container_name: ${APP_NAME}_redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redisdata:/data
    networks:
      - ${NETWORK_NAME}

volumes:
  pgdata:
  redisdata:
  ${VOLUME_NAME}:
  ${BACKUP_VOLUME_NAME}:

networks:
  ${NETWORK_NAME}:
    driver: bridge
COMPOSEEOF
    
    log_success "docker-compose.yml created at $COMPOSE_FILE"
}

# Install function
do_install() {
    log_info "Starting installation of ${APP_NAME}..."
    
    check_docker
    check_compose
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    generate_env
    generate_compose
    
    log_info "Pulling latest images..."
    $COMPOSE_CMD pull
    
    log_info "Starting services..."
    $COMPOSE_CMD up -d
    
    log_success "Installation complete!"
    log_info "Access the application at: http://localhost:8000"
    log_info "Manage with: ./litequeue.sh <command>"
}

# Start function
do_start() {
    check_docker
    check_compose
    
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "docker-compose.yml not found. Run './litequeue.sh install' first."
        exit 1
    fi
    
    cd "$INSTALL_DIR"
    log_info "Starting services..."
    $COMPOSE_CMD up -d
    log_success "Services started."
}

# Stop function
do_stop() {
    check_docker
    check_compose
    
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "docker-compose.yml not found."
        exit 1
    fi
    
    cd "$INSTALL_DIR"
    log_info "Stopping services..."
    $COMPOSE_CMD down
    log_success "Services stopped."
}

# Restart function
do_restart() {
    do_stop
    sleep 2
    do_start
}

# Status function
do_status() {
    check_docker
    
    log_info "Container Status:"
    docker ps -a --filter "name=${APP_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    log_info "Disk Usage:"
    docker system df -v | grep -E "(Name|${APP_NAME})" || true
}

# Logs function
do_logs() {
    check_docker
    
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "docker-compose.yml not found."
        exit 1
    fi
    
    cd "$INSTALL_DIR"
    log_info "Streaming logs (Ctrl+C to stop)..."
    $COMPOSE_CMD logs -f "${1:-app}"
}

# Backup function
do_backup() {
    check_docker
    
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "docker-compose.yml not found."
        exit 1
    fi
    
    BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="${INSTALL_DIR}/backups/backup_${BACKUP_DATE}.tar.gz"
    
    mkdir -p "${INSTALL_DIR}/backups"
    
    log_info "Creating database backup..."
    docker exec ${DB_CONTAINER_NAME} pg_dump -U litequeue litequeue | gzip > "${INSTALL_DIR}/backups/db_${BACKUP_DATE}.sql.gz"
    
    log_info "Creating volume backup..."
    docker run --rm \
        -v ${VOLUME_NAME}:/source:ro \
        -v ${INSTALL_DIR}/backups:/backup \
        alpine tar -czf /backup/volume_${BACKUP_DATE}.tar.gz -C /source .
    
    log_success "Backup completed: ${BACKUP_FILE}"
    log_info "Backups stored in: ${INSTALL_DIR}/backups/"
}

# Restore function
do_restore() {
    check_docker
    
    if [ -z "$1" ]; then
        log_error "Usage: ./litequeue.sh restore <backup_file.sql.gz>"
        exit 1
    fi
    
    BACKUP_FILE="$1"
    
    if [ ! -f "$BACKUP_FILE" ]; then
        log_error "Backup file not found: $BACKUP_FILE"
        exit 1
    fi
    
    log_warn "Restoring will overwrite current data. Continue? (y/n)"
    read -r confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || exit 1
    
    log_info "Stopping services..."
    do_stop
    
    log_info "Restoring database..."
    gunzip -c "$BACKUP_FILE" | docker exec -i ${DB_CONTAINER_NAME} psql -U litequeue litequeue
    
    log_info "Starting services..."
    do_start
    
    log_success "Restore completed."
}

# Prune function (Cleanup)
do_prune() {
    check_docker
    log_warn "This will remove all unused containers, networks, and dangling images. Continue? (y/n)"
    read -r confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || exit 1
    
    log_info "Cleaning up Docker resources..."
    docker system prune -f
    log_success "Cleanup completed."
}

# Update function
do_update() {
    check_docker
    check_compose
    
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "docker-compose.yml not found."
        exit 1
    fi
    
    log_info "Pulling latest images..."
    cd "$INSTALL_DIR"
    $COMPOSE_CMD pull
    
    log_info "Recreating containers with new images..."
    $COMPOSE_CMD up -d --force-recreate
    
    log_success "Update completed."
}

# Uninstall function
do_uninstall() {
    check_docker
    check_compose
    
    log_warn "WARNING: This will remove all containers, volumes, and data for ${APP_NAME}!"
    log_warn "Are you sure? Type 'DELETE' to confirm:"
    read -r confirm
    [[ "$confirm" == "DELETE" ]] || exit 1
    
    log_info "Stopping and removing services..."
    cd "$INSTALL_DIR"
    $COMPOSE_CMD down -v
    
    log_info "Removing installation directory..."
    cd ~
    rm -rf "$INSTALL_DIR"
    
    log_info "Removing unused images..."
    docker image prune -f
    
    log_success "Uninstallation complete."
}

# Help function
show_help() {
    cat << HELPEOF
${APP_NAME} Management Script

Usage: ./litequeue.sh <command> [options]

Commands:
  install       Initialize and start the application (One-click setup)
  start         Start existing services
  stop          Stop running services
  restart       Restart services
  status        Show container status and resource usage
  logs [svc]    View logs (default: app)
  backup        Create a full backup of database and volumes
  restore <file> Restore from a database backup file
  update        Pull latest images and recreate containers
  prune         Clean up unused Docker resources
  uninstall     Remove everything (WARNING: Data loss)
  help          Show this help message

Examples:
  ./litequeue.sh install
  ./litequeue.sh logs db
  ./litequeue.sh restore ./backups/db_20231010_120000.sql.gz

Optimized for: Linux, Termux (Android), Raspberry Pi
HELPEOF
}

# Main execution
case "${1:-help}" in
    install)
        do_install
        ;;
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    restart)
        do_restart
        ;;
    status)
        do_status
        ;;
    logs)
        do_logs "$2"
        ;;
    backup)
        do_backup
        ;;
    restore)
        do_restore "$2"
        ;;
    update)
        do_update
        ;;
    prune)
        do_prune
        ;;
    uninstall)
        do_uninstall
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
