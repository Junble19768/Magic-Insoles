#!/usr/bin/env bash
# One-time ECS bootstrap for magic-insoles (Scheme A).
# Backend: backend_prod/ only
# Run on server: bash /tmp/magic-deploy/server-init.sh

set -euo pipefail

REMOTE_ROOT="/var/www/magic-insoles"
BACKEND_DIR="backend_prod"
FRONT_DIST="/var/www/insoles/dist"
CORP_DIST="/var/www/corp/dist"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ">>> Installing system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq nginx python3-venv python3-pip

echo ">>> Creating web directories..."
mkdir -p "$FRONT_DIST" "$CORP_DIST" "$REMOTE_ROOT/$BACKEND_DIR/data"

if [ ! -f "$CORP_DIST/index.html" ]; then
  cat >"$CORP_DIST/index.html" <<'EOF'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>Corporate Site Placeholder</title>
</head>
<body>
  <h1>官网占位页</h1>
  <p>请将外部官网 build 产物部署到 <code>/var/www/corp/dist</code>。</p>
  <p><a href="/insoles/">进入 magic-insoles 应用</a></p>
</body>
</html>
EOF
fi

echo ">>> Installing Nginx config..."
cp "$SCRIPT_DIR/nginx.conf" /etc/nginx/conf.d/magic-insoles.conf
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx
systemctl restart nginx

echo ">>> Installing systemd unit..."
cp "$SCRIPT_DIR/magic-insoles-api.service" /etc/systemd/system/magic-insoles-api.service
systemctl daemon-reload
systemctl enable magic-insoles-api

echo ">>> Preparing Python venv..."
cd "$REMOTE_ROOT"
python3 -m venv venv
source venv/bin/activate
if [ -f "$REMOTE_ROOT/$BACKEND_DIR/requirements.txt" ]; then
  pip install -q -r "$BACKEND_DIR/requirements.txt"
fi
if [ ! -f "$REMOTE_ROOT/$BACKEND_DIR/.env" ] && [ -f "$REMOTE_ROOT/$BACKEND_DIR/.env.example" ]; then
  cp "$REMOTE_ROOT/$BACKEND_DIR/.env.example" "$REMOTE_ROOT/$BACKEND_DIR/.env"
fi
chown -R root:www-data "$REMOTE_ROOT"
chmod -R g+rX "$REMOTE_ROOT"
chown -R www-data:www-data "$REMOTE_ROOT/$BACKEND_DIR/data"

echo ">>> Server init done."
echo "    Next: run deploy/deploy.ps1 from your dev machine."
