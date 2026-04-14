#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "No .env found. Run ./setup.sh first."
  exit 1
fi

source "$ENV_FILE"

export PATH="$TIZEN_PATH/tools/ide/bin:$TIZEN_PATH/tools:$PATH"
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-21-openjdk}"

APP="PlxBridge0.PlexBridge"

echo "==> Packaging..."
tizen package -t wgt -s "$PROFILE" -- "$DIR"

cp "$DIR/PlexBridge.wgt" /tmp/plexbridge.wgt

echo "==> Installing..."
tizen install -n plexbridge.wgt -t "$TV_NAME" -- /tmp

echo "==> Launching..."
tizen run -p "$APP" -t "$TV_NAME"

echo "==> Done!"
