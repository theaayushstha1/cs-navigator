#!/bin/bash
set -euo pipefail

# Always run from the folder where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Enable BuildKit for better cross-platform builds
export DOCKER_BUILDKIT=1

# Config
DOCKER_USERNAME="sakina593"
FRONTEND_IMAGE="${DOCKER_USERNAME}/chatbot-frontend"
BACKEND_IMAGE="${DOCKER_USERNAME}/chatbot-backend"

EC2_HOST="18.214.136.155"
EC2_USER="ec2-user"
EC2_KEY="cs-chatbot-key.pem"

API_URL="http://${EC2_HOST}:5000"

log(){ echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"; }
die(){ echo "[ERROR] $1" >&2; exit 1; }

check_prerequisites() {
  command -v docker >/dev/null 2>&1 || die "Docker is not installed"
  command -v ssh   >/dev/null 2>&1 || die "SSH is not installed"

  [ -f "$EC2_KEY" ] || die "PEM key not found: $SCRIPT_DIR/$EC2_KEY"
  chmod 400 "$EC2_KEY" 2>/dev/null || true

  docker info >/dev/null 2>&1 || die "Docker daemon is not running"
  [ -f "$SCRIPT_DIR/docker-compose.yml" ] || die "docker-compose.yml not found in $SCRIPT_DIR"
}

build_images() {
  log "Building frontend (locally)..."
  docker buildx build \
    --build-arg VITE_API_BASE_URL="${API_URL}" \
    --platform linux/amd64 \
    --load \
    -t "${FRONTEND_IMAGE}:latest" \
    "$SCRIPT_DIR/frontend" || die "Frontend build failed"

  log "Building backend (locally)..."
  docker buildx build \
    --platform linux/amd64 \
    --load \
    -t "${BACKEND_IMAGE}:latest" \
    "$SCRIPT_DIR/backend" || die "Backend build failed"
}

push_images() {
  log "Pushing images to Docker Hub..."
  if ! docker info 2>/dev/null | grep -q "Username: ${DOCKER_USERNAME}"; then
    docker login || die "Docker login failed"
  fi
  docker push "${FRONTEND_IMAGE}:latest" || die "Frontend push failed"
  docker push "${BACKEND_IMAGE}:latest"  || die "Backend push failed"
}

test_ssh() {
  log "Testing SSH..."
  ssh -i "$EC2_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no \
    "${EC2_USER}@${EC2_HOST}" "echo ok" >/dev/null 2>&1 || die "SSH failed (check key + SG)"
}

deploy_to_ec2() {
  log "Copying docker-compose.yml and .env to EC2..."
  scp -i "$EC2_KEY" -o StrictHostKeyChecking=no \
    "$SCRIPT_DIR/docker-compose.yml" "$SCRIPT_DIR/.env" "${EC2_USER}@${EC2_HOST}:~/" || die "SCP failed"

  log "Deploying on EC2 (pull only, no build)..."
  ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_HOST}" << 'EOF'
set -e
echo "Pulling latest images..."
docker pull sakina593/chatbot-frontend:latest
docker pull sakina593/chatbot-backend:latest
echo "Stopping old containers..."
docker-compose down || true
echo "Cleaning up old images..."
docker image prune -f
echo "Starting new containers..."
docker-compose up -d
echo "Container status:"
docker-compose ps
EOF
}

main() {
  log "========================================="
  log "Starting deployment..."
  log "========================================="
  check_prerequisites
  build_images
  push_images
  test_ssh
  deploy_to_ec2
  log "========================================="
  log "Deployment complete!"
  log "Frontend: http://${EC2_HOST}:3000"
  log "Backend:  http://${EC2_HOST}:5000"
  log "========================================="
}

main "$@"
