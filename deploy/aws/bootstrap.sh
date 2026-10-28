#!/usr/bin/env bash
# =============================================================================
# bootstrap.sh — one-time software setup of the EC2 host (Ubuntu 24.04, x86_64)
# =============================================================================
# Creates no AWS resources: launch the instance, attach the volume and assign
# the Elastic IP yourself first. Then, from the repo root:
#
#   scp -r deploy/aws ubuntu@<ip>:~/aws-setup
#   ssh ubuntu@<ip> 'sudo bash ~/aws-setup/bootstrap.sh <elastic-ip> you@example.com'
#
# <host> is the Elastic IP for now. Let's Encrypt issues IP certificates only
# as 6-day "shortlived" certs (certbot >= 5.3); the certbot timer renews them.
# Once a domain exists, re-run with the domain: the cert is reissued for it.
#
# Safe to re-run: every step skips what is already in place.
# =============================================================================

set -euo pipefail

HOST="${1:-}"
EMAIL="${2:-}"
DEPLOY_USER="${DEPLOY_USER:-ubuntu}"
SWAP_SIZE="${SWAP_SIZE:-2G}"
APP_DIR=/opt/saiseeds
WEBROOT=/var/www/certbot
CERT_NAME=saiseeds
SITE=/etc/nginx/sites-available/saiseeds
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "$HOST" || -z "$EMAIL" ]]; then
    echo "Usage: sudo bash bootstrap.sh <elastic-ip-or-domain> <letsencrypt-email>" >&2
    exit 1
fi
if [[ "$(id -u)" -ne 0 ]]; then
    echo "Run as root (sudo)." >&2
    exit 1
fi

echo "[bootstrap] Installing docker, nginx ..."
apt-get update -q
DEBIAN_FRONTEND=noninteractive apt-get install -y -q \
    docker.io docker-compose-v2 nginx curl openssl snapd
systemctl enable --now docker
usermod -aG docker "$DEPLOY_USER"

# Ubuntu's apt certbot is too old for IP certificates; the snap tracks upstream.
echo "[bootstrap] Installing certbot (snap) ..."
snap install --classic certbot
ln -sf /snap/bin/certbot /usr/bin/certbot

# Cap container logs: the 10 GB volume must not fill up with json logs.
if [[ ! -f /etc/docker/daemon.json ]]; then
    echo "[bootstrap] Capping docker logs ..."
    cat > /etc/docker/daemon.json <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
EOF
    systemctl restart docker
fi

# Swap keeps a 1-2 GB instance from OOM-killing gunicorn under load.
if ! swapon --show | grep -q /swapfile; then
    echo "[bootstrap] Adding ${SWAP_SIZE} swap ..."
    fallocate -l "$SWAP_SIZE" /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "[bootstrap] Preparing ${APP_DIR} ..."
install -d -m 750 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$APP_DIR"
if [[ ! -f "$APP_DIR/.env" ]]; then
    install -m 600 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$SCRIPT_DIR/env.example" "$APP_DIR/.env"
    echo "[bootstrap] Wrote ${APP_DIR}/.env from env.example: fill in the real values."
fi
install -d -m 755 "$WEBROOT"
ln -sf "$SITE" /etc/nginx/sites-enabled/saiseeds
rm -f /etc/nginx/sites-enabled/default

# --- Certificate ------------------------------------------------------------
CERT_FILE="/etc/letsencrypt/live/${CERT_NAME}/cert.pem"
cert_covers_host() {
    [[ -f "$CERT_FILE" ]] \
        && openssl x509 -in "$CERT_FILE" -noout -ext subjectAltName | grep -qwF "$HOST"
}

if ! cert_covers_host; then
    if [[ "$HOST" =~ ^[0-9]+(\.[0-9]+){3}$ ]]; then
        certbot_version="$(certbot --version | awk '{print $2}')"
        if [[ "$(printf '%s\n' 5.3.0 "$certbot_version" | sort -V | head -1)" != "5.3.0" ]]; then
            echo "[bootstrap] certbot ${certbot_version} is too old for IP certificates (need 5.3+)." >&2
            exit 1
        fi
        identifier=(--ip-address "$HOST" --preferred-profile shortlived)
    else
        identifier=(-d "$HOST")
    fi

    # The full site points at a certificate that does not exist yet, so serve
    # only the ACME challenge until certbot has one.
    echo "[bootstrap] Serving the ACME challenge for ${HOST} ..."
    cat > "$SITE" <<EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    location /.well-known/acme-challenge/ { root ${WEBROOT}; }
    location / { return 404; }
}
EOF
    nginx -t
    systemctl reload nginx

    echo "[bootstrap] Requesting certificate for ${HOST} ..."
    if ! certbot certonly --webroot -w "$WEBROOT" --cert-name "$CERT_NAME" \
        "${identifier[@]}" -m "$EMAIL" --agree-tos --non-interactive \
        --deploy-hook "systemctl reload nginx"; then
        echo "[bootstrap] certbot failed. Check that ${HOST} is this instance's" >&2
        echo "  public address and port 80 is open, then re-run this script." >&2
        exit 1
    fi
fi

echo "[bootstrap] Installing nginx site for ${HOST} ..."
sed "s/__HOST__/${HOST}/g" "$SCRIPT_DIR/nginx.conf.template" > "$SITE"
nginx -t
systemctl reload nginx

echo "[bootstrap] Done. Next:"
echo "  1. Fill in ${APP_DIR}/.env (ALLOWED_HOSTS=${HOST})"
echo "  2. Run the 'Deploy AWS' workflow (or push to master)"
