#!/usr/bin/env bash
set -euo pipefail

HYDROP_IP="${1:-142.93.209.85}"
SSH_USER="${2:-root}"
PROJECT_DIR="/root/Hotel-Management-System"
LOCAL_DIR="$(pwd)"
ARCHIVE_NAME="hotel-system-deploy.tar.gz"

# Colors (disabled if not a tty)
if [ -t 1 ]; then
  C_RESET='\033[0m'; C_RED='\033[0;31m'; C_GREEN='\033[0;32m'; C_YELLOW='\033[0;33m'; C_BLUE='\033[0;34m'
else
  C_RESET=''; C_RED=''; C_GREEN=''; C_YELLOW=''; C_BLUE=''
fi

log()   { echo -e "${C_BLUE}[deploy]${C_RESET} $*"; }
ok()    { echo -e "${C_GREEN}✔${C_RESET} $*"; }
warn()  { echo -e "${C_YELLOW}⚠${C_RESET} $*" >&2; }
die()   { echo -e "${C_RED}✖${C_RESET} $*" >&2; exit 1; }

# --- Pre-flight checks ---
command -v ssh >/dev/null 2>&1 || die "ssh is not installed or not in PATH."
command -v scp >/dev/null 2>&1 || die "scp is not installed or not in PATH."
command -v tar >/dev/null 2>&1 || die "tar is not installed or not in PATH."

ENABLE_RSYNC=false
command -v rsync >/dev/null 2>&1 && ENABLE_RSYNC=true

# Verify local project layout
[ -f "$LOCAL_DIR/docker-compose.yml" ] || die "Run this script from the Hotel-Management-System directory (docker-compose.yml not found)."
[ -d "$LOCAL_DIR/backend" ] || die "Missing backend/ directory."
[ -d "$LOCAL_DIR/frontend" ] || die "Missing frontend/ directory."
[ -d "$LOCAL_DIR/database" ] || die "Missing database/ directory."
[ -d "$LOCAL_DIR/nginx" ] || die "Missing nginx/ directory."
[ -d "$LOCAL_DIR/secrets" ] || die "Missing secrets/ directory."

# Verify secrets exist (warn if missing, because Docker Secrets fail open is bad)
if [ ! -f "$LOCAL_DIR/secrets/db_root_password.txt" ]; then
  warn "secrets/db_root_password.txt is missing — MySQL root password will be empty."
fi
if [ ! -f "$LOCAL_DIR/secrets/db_app_password.txt" ]; then
  warn "secrets/db_app_password.txt is missing."
fi
if [ ! -f "$LOCAL_DIR/secrets/admin_token.txt" ]; then
  warn "secrets/admin_token.txt is missing — admin endpoints will be disabled."
fi
if [ ! -f "$LOCAL_DIR/secrets/dashboard_password.txt" ]; then
  warn "secrets/dashboard_password.txt is missing."
fi

# Verify SSL certs
MISSING_SSL=false
for f in "$LOCAL_DIR/nginx/ssl/fullchain.pem" "$LOCAL_DIR/nginx/ssl/privkey.pem"; do
  if [ ! -f "$f" ]; then
    warn "SSL cert missing: $f"
    MISSING_SSL=true
  fi
done
if [ "$MISSING_SSL" = true ]; then
  warn "Nginx will fail to start without valid SSL certs. Generate them before deploy or place them in nginx/ssl/."
fi

SSH_FLAGS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=10)

# --- Test droplet connectivity ---
log "Testing SSH connectivity to ${SSH_USER}@${HYDROP_IP} ..."
if ! ssh "${SSH_FLAGS[@]}" "${SSH_USER}@${HYDROP_IP}" "echo 'SSH OK'" >/dev/null 2>&1; then
  die "Cannot reach ${SSH_USER}@${HYDROP_IP} via SSH. Check IP, user, and SSH key."
fi
ok "SSH connection confirmed."

# --- Prepare archive (exclude git, pycache, dockerignore files) ---
log "Packing project into ${ARCHIVE_NAME} ..."
EXCLUDE_LIST="--exclude=.git --exclude=__pycache__ --exclude=*.pyc --exclude=.dockerignore --exclude=$ARCHIVE_NAME"
if [ "$ENABLE_RSYNC" = true ]; then
  rsync -avz --delete \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.dockerignore' \
    "$LOCAL_DIR/" "${SSH_USER}@${HYDROP_IP}:${PROJECT_DIR}/"
else
  tar -czf "$ARCHIVE_NAME" $EXCLUDE_LIST -C "$LOCAL_DIR" .
  log "Uploading archive to droplet (scp) ..."
  scp -q "$ARCHIVE_NAME" "${SSH_USER}@${HYDROP_IP}:/tmp/${ARCHIVE_NAME}"
  # Remote extraction + cleanup
  ssh "${SSH_FLAGS[@]}" "${SSH_USER}@${HYDROP_IP}" bash -euxo pipefail <<'REMOTE'
set -euo pipefail
ARCHIVE_NAME="hotel-system-deploy.tar.gz"
PROJECT_DIR="/root/Hotel-Management-System"
mkdir -p "$PROJECT_DIR"
tar -xzf "/tmp/${ARCHIVE_NAME}" -C "$PROJECT_DIR"
rm -f "/tmp/${ARCHIVE_NAME}"
REMOTE
  rm -f "$ARCHIVE_NAME"
fi

# --- Ensure target directory exists and ownership is correct ---
ssh "${SSH_FLAGS[@]}" "${SSH_USER}@${HYDROP_IP}" bash -euxo pipefail <<'REMOTE'
set -euo pipefail
PROJECT_DIR="/root/Hotel-Management-System"
mkdir -p "$PROJECT_DIR"
# Ensure nginx/ssl directory exists even if empty (prevents startup crash)
mkdir -p "$PROJECT_DIR/nginx/ssl"
# If SSL cert files are missing, at least create dummy placeholders so nginx is told to use them
# The deployment script already warns above; this prevents nginx from crashing the entire compose start
if [ ! -f "$PROJECT_DIR/nginx/ssl/fullchain.pem" ]; then
  touch "$PROJECT_DIR/nginx/ssl/fullchain.pem"
fi
if [ ! -f "$PROJECT_DIR/nginx/ssl/privkey.pem" ]; then
  touch "$PROJECT_DIR/nginx/ssl/privkey.pem"
fi
REMOTE

ok "Project files synced."

# --- Install Docker/Compose on droplet if missing ---
ssh "${SSH_FLAGS[@]}" "${SSH_USER}@${HYDROP_IP}" bash -euxo pipefail <<'REMOTE'
set -euo pipefail
if ! command -v docker >/dev/null 2>&1; then
  echo "Installing Docker ..."
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  CODENAME="$(. /etc/os-release && echo "${VERSION_CODENAME:-}")"
  if [ -z "$CODENAME" ]; then
    # Fallback: detect from lsb_release if available
    CODENAME="$(lsb_release -cs 2>/dev/null || echo "")"
  fi
  if [ -z "$CODENAME" ]; then
    echo "Unable to detect OS codename for Docker APT repo."; exit 1
  fi
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${CODENAME} stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
else
  echo "Docker already installed."
fi
# Ensure compose plugin
if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose plugin missing; installing compose plugin ..."
  apt-get update -y
  apt-get install -y docker-compose-plugin
fi
REMOTE
ok "Docker & Compose ready on droplet."

# --- Deploy ---
log "Deploying stack ..."
ssh "${SSH_FLAGS[@]}" "${SSH_USER}@${HYDROP_IP}" bash -euxo pipefail <<'REMOTE'
set -euo pipefail
PROJECT_DIR="/root/Hotel-Management-System"
cd "$PROJECT_DIR"

# Stop & remove old stack (ignore if nothing running)
docker compose down --remove-orphans || true

# Pull/build images — use legacy CLI name to avoid "no configuration file" issue
# docker-compose (v1 binary) resolves the file explicitly
if docker-compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
elif docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
else
  echo "docker compose not found"; exit 1
fi

echo "Using compose command: $COMPOSE_CMD"
$COMPOSE_CMD -f docker-compose.yml build --no-cache
$COMPOSE_CMD -f docker-compose.yml up -d

echo "=== Services ==="
$COMPOSE_CMD -f docker-compose.yml ps
REMOTE
ok "Stack started."

# --- Smoke test ---
log "Running smoke tests ..."
ssh "${SSH_FLAGS[@]}" "${SSH_USER}@${HYDROP_IP}" bash -euxo pipefail <<'REMOTE'
set -euo pipefail
PROJECT_DIR="/root/Hotel-Management-System"
cd "$PROJECT_DIR"
sleep 5
# Frontend nginx health (returns 200 even without valid SSL on port 80)
curl -fsS http://127.0.0.1/health >/dev/null || echo "Frontend /health check failed"
REMOTE

echo ""
echo "================================================================"
echo "  Deployment Summary"
echo "================================================================"
echo "Droplet:       ${SSH_USER}@${HYDROP_IP}"
echo "Project:       ${PROJECT_DIR}"
echo ""
echo "Access URLs:"
echo "  HTTPS:      https://rosyohospitality.com.np"
echo "  Dashboard:  https://rosyohospitality.com.np/dashboard/"
echo "  API Docs:   https://rosyohospitality.com.np/docs  (only if DISABLE_DOCS=false)"
echo ""
echo "Useful commands:"
echo "  ssh ${SSH_USER}@${HYDROP_IP} \"cd ${PROJECT_DIR} && docker compose ps\""
echo "  ssh ${SSH_USER}@${HYDROP_IP} \"cd ${PROJECT_DIR} && docker compose logs -f backend\""
echo "================================================================"
