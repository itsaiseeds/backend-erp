#!/usr/bin/env bash
# =============================================================================
# deploy.sh — runs ON the EC2 host; called over SSH by deploy-aws.yml
# =============================================================================
# Usage: bash /opt/saiseeds/deploy.sh <image.tar.gz> <host> <tag>
#
# Loads the image the workflow built, swaps the web container, and waits for
# Django to answer. If it never does, the previous image is put back.
# Keeps only saiseeds-web:latest and :previous so the 10 GB disk never fills.
# =============================================================================

set -euo pipefail

TARBALL="$1"
API_HOST="$2"
TAG="$3"
APP_DIR=/opt/saiseeds
IMAGE=saiseeds-web
COMPOSE=(docker compose -f "$APP_DIR/docker-compose.prod.yml")

cd "$APP_DIR"

echo "[deploy] Loading ${IMAGE}:${TAG} ..."
gunzip -c "$TARBALL" | docker load
rm -f "$TARBALL"

if docker image inspect "${IMAGE}:latest" >/dev/null 2>&1; then
    docker tag "${IMAGE}:latest" "${IMAGE}:previous"
fi
docker tag "${IMAGE}:${TAG}" "${IMAGE}:latest"

echo "[deploy] Starting web ..."
"${COMPOSE[@]}" up -d --remove-orphans

# Hit Django directly (not through nginx) with the headers nginx would send, so
# ALLOWED_HOSTS and SECURE_SSL_REDIRECT see a normal https request. Startup
# runs collectstatic against the image and a query on Neon, so allow ~2 min.
healthy() {
    local code
    code=$(curl -s -o /dev/null -w '%{http_code}' \
        -H "Host: ${API_HOST}" -H "X-Forwarded-Proto: https" \
        http://127.0.0.1:8000/admin/login/ || true)
    [[ "$code" == "200" ]]
}

for _ in $(seq 1 60); do
    if healthy; then
        echo "[deploy] Healthy."
        docker rmi "${IMAGE}:${TAG}" >/dev/null 2>&1 || true
        # Drop every other saiseeds-web tag and any dangling layers.
        docker images "$IMAGE" --format '{{.Repository}}:{{.Tag}}' \
            | grep -vE ":(latest|previous)$" | xargs -r docker rmi >/dev/null 2>&1 || true
        docker image prune -f >/dev/null
        df -h / | tail -1
        exit 0
    fi
    sleep 2
done

echo "[deploy] Not healthy after 2 minutes. Last logs:" >&2
"${COMPOSE[@]}" logs --tail 50 web >&2 || true

if docker image inspect "${IMAGE}:previous" >/dev/null 2>&1; then
    echo "[deploy] Rolling back to the previous image ..." >&2
    docker tag "${IMAGE}:previous" "${IMAGE}:latest"
    "${COMPOSE[@]}" up -d --remove-orphans
fi
exit 1
