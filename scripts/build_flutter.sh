#!/bin/bash
set -e

FLUTTER_DIR="/opt/flutter"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_DIR="$SCRIPT_DIR/../web"

# Install Flutter if not present
if [ ! -d "$FLUTTER_DIR" ]; then
    echo "[flutter] Installing Flutter SDK ..."
    apt-get update && apt-get install -y curl git unzip xz-utils zip
    git clone https://github.com/flutter/flutter.git -b stable "$FLUTTER_DIR"
fi

export PATH="$FLUTTER_DIR/bin:$PATH"

echo "[flutter] Building web app ..."
cd "$WEB_DIR"
flutter pub get
flutter build web --release --base-href /sales-admin/

echo "[flutter] Build complete: web/build/web/"
